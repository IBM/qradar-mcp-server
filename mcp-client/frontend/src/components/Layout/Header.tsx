import {
  Header as CarbonHeader,
  HeaderName,
  HeaderGlobalBar,
  HeaderGlobalAction,
} from '@carbon/react';
import {
  Settings,
  SidePanelOpen,
  SidePanelClose,
} from '@carbon/icons-react';
import { useUIStore } from '../../store';

export default function Header() {
  const { sidebarOpen, toggleSidebar, openSettings } = useUIStore();

  return (
    <CarbonHeader aria-label="IBM MCP Client">
      <HeaderGlobalAction
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
        onClick={toggleSidebar}
      >
        {sidebarOpen ? <SidePanelClose size={20} /> : <SidePanelOpen size={20} />}
      </HeaderGlobalAction>
      
      <HeaderName href="/" prefix="">
        IBM MCP Client
      </HeaderName>

      <HeaderGlobalBar>
        <HeaderGlobalAction
          aria-label="Settings"
          onClick={() => openSettings('qradar')}
        >
          <Settings size={20} />
        </HeaderGlobalAction>
      </HeaderGlobalBar>
    </CarbonHeader>
  );
}
