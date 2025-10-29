"""generative_agents.model.llm_model"""

import time
import re
import requests
from prometheus_client import Counter, Histogram, REGISTRY

# Prometheus metrics for Ollama usage and performance (idempotent creation)

def _get_or_create_counter(name, documentation, labelnames=()):
    try:
        return Counter(name, documentation, labelnames)
    except ValueError:
        # Already registered in the default registry; reuse existing collector
        return REGISTRY._names_to_collectors[name]  # type: ignore[attr-defined]


def _get_or_create_histogram(name, documentation):
    try:
        return Histogram(name, documentation)
    except ValueError:
        return REGISTRY._names_to_collectors[name]  # type: ignore[attr-defined]


OLLAMA_REQUESTS_TOTAL = _get_or_create_counter(
    "ollama_requests_total", "Total number of Ollama requests", ["status"]
)
OLLAMA_REQUEST_LATENCY_SECONDS = _get_or_create_histogram(
    "ollama_request_latency_seconds", "Latency of Ollama requests in seconds"
)
OLLAMA_PROMPT_TOKENS = _get_or_create_counter(
    "ollama_prompt_tokens_total", "Total prompt tokens returned by Ollama"
)
OLLAMA_COMPLETION_TOKENS = _get_or_create_counter(
    "ollama_completion_tokens_total", "Total completion tokens returned by Ollama"
)
OLLAMA_TOTAL_TOKENS = _get_or_create_counter(
    "ollama_total_tokens_total", "Total tokens (prompt+completion) returned by Ollama"
)


class LLMModel:
    def __init__(self, config):
        self._api_key = config["api_key"]
        self._base_url = config["base_url"]
        self._model = config["model"]
        self._meta_responses = []
        self._summary = {"total": [0, 0, 0]}

        self._handle = self.setup(config)
        self._enabled = True

    def setup(self, config):
        raise NotImplementedError(
            "setup is not support for " + str(self.__class__)
        )

    def completion(
        self,
        prompt,
        retry=10,
        callback=None,
        failsafe=None,
        caller="llm_normal",
        **kwargs
    ):
        response, self._meta_responses = None, []
        self._summary.setdefault(caller, [0, 0, 0])
        for _ in range(retry):
            try:
                meta_response = self._completion(prompt, **kwargs).strip()
                self._meta_responses.append(meta_response)
                self._summary["total"][0] += 1
                self._summary[caller][0] += 1
                if callback:
                    response = callback(meta_response)
                else:
                    response = meta_response
            except Exception as e:
                print(f"LLMModel.completion() caused an error: {e}")
                time.sleep(5)
                response = None
                continue
            if response is not None:
                break
        pos = 2 if response is None else 1
        self._summary["total"][pos] += 1
        self._summary[caller][pos] += 1
        return response or failsafe

    def _completion(self, prompt, **kwargs):
        raise NotImplementedError(
            "_completion is not support for " + str(self.__class__)
        )

    def is_available(self):
        return self._enabled  # and self._summary["total"][2] <= 10

    def get_summary(self):
        des = {}
        for k, v in self._summary.items():
            des[k] = "S:{},F:{}/R:{}".format(v[1], v[2], v[0])
        return {"model": self._model, "summary": des}

    def disable(self):
        self._enabled = False

    @property
    def meta_responses(self):
        return self._meta_responses


class OpenAILLMModel(LLMModel):
    def setup(self, config):
        from openai import OpenAI

        return OpenAI(api_key=self._api_key, base_url=self._base_url)

    def _completion(self, prompt, temperature=0.5):
        messages = [{"role": "user", "content": prompt}]
        response = self._handle.chat.completions.create(
            model=self._model, messages=messages, temperature=temperature
        )
        if len(response.choices) > 0:
            return response.choices[0].message.content
        return ""


class OllamaLLMModel(LLMModel):
    def setup(self, config):
        return None

    def ollama_chat(self, messages, temperature):
        headers = {
            "Content-Type": "application/json"
        }
        params = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        start = time.time()
        status = "error"
        try:
            response = requests.post(
                url=f"{self._base_url}/chat/completions",
                headers=headers,
                json=params,
                stream=False,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            status = "success"
            # Try to read usage from OpenAI-compatible response
            usage = data.get("usage", {})
            if isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_tokens")
                completion_tokens = usage.get("completion_tokens")
                total_tokens = usage.get("total_tokens")
                if isinstance(prompt_tokens, int):
                    OLLAMA_PROMPT_TOKENS.inc(prompt_tokens)
                if isinstance(completion_tokens, int):
                    OLLAMA_COMPLETION_TOKENS.inc(completion_tokens)
                if isinstance(total_tokens, int):
                    OLLAMA_TOTAL_TOKENS.inc(total_tokens)
            return data
        finally:
            elapsed = time.time() - start
            OLLAMA_REQUEST_LATENCY_SECONDS.observe(elapsed)
            OLLAMA_REQUESTS_TOTAL.labels(status=status).inc()

    def _completion(self, prompt, temperature=0.5):
        if "qwen3" in self._model and "\n/nothink" not in prompt:
            # 针对Qwen3模型禁用think，提高推理速度
            prompt += "\n/nothink"
        messages = [{"role": "user", "content": prompt}]
        response = self.ollama_chat(messages=messages, temperature=temperature)
        if response and len(response["choices"]) > 0:
            ret = response["choices"][0]["message"]["content"]
            # 从输出结果中过滤掉<think>标签内的文字，以免影响后续逻辑
            return re.sub(r"<think>.*</think>", "", ret, flags=re.DOTALL)
        return ""


def create_llm_model(llm_config):
    """Create llm model"""

    if llm_config["provider"] == "ollama":
        return OllamaLLMModel(llm_config)

    elif llm_config["provider"] == "openai":
        return OpenAILLMModel(llm_config)
    else:
        raise NotImplementedError(
            "llm provider {} is not supported".format(llm_config["provider"])
        )
    return None


def parse_llm_output(response, patterns, mode="match_last", ignore_empty=False):
    if isinstance(patterns, str):
        patterns = [patterns]
    rets = []
    for line in response.split("\n"):
        line = line.replace("**", "").strip()
        for pattern in patterns:
            if pattern:
                matchs = re.findall(pattern, line)
            else:
                matchs = [line]
            if len(matchs) >= 1:
                rets.append(matchs[0])
                break
    if not ignore_empty:
        assert rets, "Failed to match llm output"
    # When ignore_empty is True and nothing matched, return None gracefully
    if not rets:
        return None
    if mode == "match_first":
        return rets[0]
    if mode == "match_last":
        return rets[-1]
    if mode == "match_all":
        return rets
    return None
