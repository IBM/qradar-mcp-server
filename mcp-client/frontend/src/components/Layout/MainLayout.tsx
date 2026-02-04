import Header from './Header';
import Sidebar from '../Sidebar/Sidebar';
import ChatContainer from '../Chat/ChatContainer';
import SettingsModal from '../Settings/SettingsModal';
import { useUIStore } from '../../store';

export default function MainLayout() {
  const { sidebarOpen, settingsOpen } = useUIStore();

  return (
    <div className="app-layout">
      <Header />
      
      <div className="app-content">
        <Sidebar collapsed={!sidebarOpen} />
        <ChatContainer />
      </div>

      {settingsOpen && <SettingsModal />}
    </div>
  );
}
