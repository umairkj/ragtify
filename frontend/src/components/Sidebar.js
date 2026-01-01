import React from 'react';
import { ChatIcon, SettingsIcon, DatabaseIcon } from './Icons';
import RagtifyLogo from './RagtifyLogo';

const Sidebar = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'chat', label: 'Chat', icon: ChatIcon },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
    { id: 'context', label: 'Context Browser', icon: DatabaseIcon },
  ];

  return (
    <div className="w-64 bg-white dark:bg-slate-800 border-r border-gray-200 dark:border-slate-700 h-screen fixed left-0 top-0 text-gray-900 dark:text-white">
      {/* Header */}
      <div className="h-[61px] px-4 border-b border-gray-200 dark:border-slate-700 flex items-center">
        <div className="flex items-center space-x-3">
          <RagtifyLogo height={30} />
        </div>
      </div>

      {/* Nav */}
      <nav className="p-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left transition-colors duration-200 ${
                activeTab === tab.id
                  ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                  : 'text-gray-600 dark:text-slate-400 hover:bg-gray-50 dark:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-slate-200'
              }`}
            >
              <Icon />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};

export default Sidebar;
