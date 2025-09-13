import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import BasicLayout from './layouts/BasicLayout';
import SimulationPage from './pages/Simulation';

function App() {
  return (
    <Router>
      <BasicLayout>
        <Routes>
          <Route path="/" element={<SimulationPage />} />
          <Route path="/simulation" element={<SimulationPage />} />
        </Routes>
      </BasicLayout>
    </Router>
  );
}

export default App;