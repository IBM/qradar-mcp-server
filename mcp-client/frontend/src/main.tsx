import React from 'react';
import ReactDOM from 'react-dom/client';
import { Theme } from '@carbon/react';
import App from './App';
import './styles/main.scss';

type CarbonTheme = 'white' | 'g10' | 'g100' | 'g90';

// Get saved theme or default to dark
const savedTheme = localStorage.getItem('ibm-mcp-theme');
const initialTheme: CarbonTheme = savedTheme === 'light' ? 'g10' : 'g100';

function Root() {
  const [theme, setTheme] = React.useState<CarbonTheme>(initialTheme);

  React.useEffect(() => {
    // Listen for theme changes
    const handleStorage = () => {
      const t = localStorage.getItem('ibm-mcp-theme');
      setTheme(t === 'light' ? 'g10' : 'g100');
    };
    
    window.addEventListener('storage', handleStorage);
    
    // Custom event for same-tab updates
    window.addEventListener('themeChange', handleStorage);
    
    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener('themeChange', handleStorage);
    };
  }, []);

  return (
    <Theme theme={theme}>
      <App />
    </Theme>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
