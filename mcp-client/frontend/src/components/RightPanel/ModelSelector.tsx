import { Dropdown } from '@carbon/react';
import { useConnectionStore } from '../../store';

export default function ModelSelector() {
  const { models, activeModelId, setActiveModel } = useConnectionStore();
  
  const activeModel = models.find(m => m.id === activeModelId);

  if (models.length === 0) {
    return (
      <span style={{ fontSize: '0.875rem', color: 'var(--cds-text-secondary)' }}>
        No models configured
      </span>
    );
  }

  return (
    <Dropdown
      id="model-selector"
      titleText=""
      label="Select Model"
      size="sm"
      items={models}
      itemToString={(item) => item?.displayName || item?.name || ''}
      selectedItem={activeModel}
      onChange={({ selectedItem }) => setActiveModel(selectedItem?.id || null)}
      style={{ minWidth: '180px' }}
    />
  );
}
