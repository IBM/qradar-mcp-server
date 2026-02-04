import { useState, useEffect } from 'react';
import { Toggle } from '@carbon/react';

export default function PreferencesPanel() {
  const [isDarkTheme, setIsDarkTheme] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem('ibm-mcp-theme');
    setIsDarkTheme(saved !== 'light');
  }, []);

  const handleThemeChange = (checked: boolean) => {
    setIsDarkTheme(checked);
    localStorage.setItem('ibm-mcp-theme', checked ? 'dark' : 'light');
    // Dispatch custom event for same-tab theme update
    window.dispatchEvent(new Event('themeChange'));
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h4 style={{ marginBottom: '1.5rem' }}>Appearance</h4>
      
      <Toggle
        id="theme-toggle"
        labelText="Theme"
        labelA="Light"
        labelB="Dark"
        toggled={isDarkTheme}
        onToggle={handleThemeChange}
      />
      
      <p style={{ 
        marginTop: '0.5rem', 
        fontSize: '0.875rem', 
        color: 'var(--cds-text-secondary)' 
      }}>
        {isDarkTheme ? 'Dark theme is enabled' : 'Light theme is enabled'}
      </p>
    </div>
  );
}
