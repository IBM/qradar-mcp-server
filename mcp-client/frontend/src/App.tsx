import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/Layout/MainLayout';
import { useConnectionStore } from './store';

function App() {
  const syncFromBackend = useConnectionStore((state) => state.syncFromBackend);

  // Sync data from backend on app load
  useEffect(() => {
    syncFromBackend();
  }, [syncFromBackend]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<MainLayout />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
