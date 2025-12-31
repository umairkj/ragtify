import React, { useState, useEffect } from 'react';
import './App.css';
import Sidebar from './components/Sidebar';
import {
  SendIcon, SaveIcon, SyncIcon, RefreshIcon, TrashIcon, PlusIcon,
  LoadingSpinner, CheckCircleIcon, ExclamationCircleIcon,
  ChatIcon, SettingsIcon, DatabaseIcon
} from './components/Icons';

const API_BASE = 'http://api.ragtify.local:8000/api/v1';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Settings state
  const [settings, setSettings] = useState({});
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsEditing, setSettingsEditing] = useState({});
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Context Browser state
  const [payloads, setPayloads] = useState([]);
  const [payloadsLoading, setPayloadsLoading] = useState(false);
  const [newPayload, setNewPayload] = useState({
    source_id: '',
    collection_name: '',
    title: '',
    description: '',
    url: ''
  });
  const [syncLoading, setSyncLoading] = useState(false);
  const [addingPayload, setAddingPayload] = useState(false);

  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Load settings when needed
  useEffect(() => {
    if (activeTab === 'settings' || activeTab === 'chat') {
      loadSettings();
    }
  }, [activeTab]);

  // Load payloads on mount
  useEffect(() => {
    if (activeTab === 'context') {
      loadPayloads();
    }
  }, [activeTab]);

  const loadSettings = async () => {
    setSettingsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/settings/`);
      const data = await res.json().catch(() => ({}));
      const settingsData = data.settings || {};
      setSettings(settingsData);
      setSettingsEditing(settingsData);
    } catch (error) {
      console.error('Failed to load settings:', error);
      alert('Failed to load settings');
    } finally {
      setSettingsLoading(false);
    }
  };

  const saveSettings = async () => {
    setSettingsLoading(true);
    setSaveSuccess(false);
    try {
      const res = await fetch(`${API_BASE}/settings/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ settings: settingsEditing }),
      });
      if (!res.ok) throw new Error('Failed to save settings');
      setSettings(settingsEditing);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
    } finally {
      setSettingsLoading(false);
    }
  };

  const loadPayloads = async () => {
    setPayloadsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/content/`);
      const data = await res.json().catch(() => []);
      setPayloads(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to load payloads:', error);
      alert('Failed to load payloads');
    } finally {
      setPayloadsLoading(false);
    }
  };

  const syncToQdrant = async () => {
    setSyncLoading(true);
    try {
      const res = await fetch(`${API_BASE}/content/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (!res.ok) throw new Error('Failed to sync to Qdrant');
      const data = await res.json();
      alert(`Sync successful! Processed ${data.content_processed || 0} items.`);
      loadPayloads();
    } catch (error) {
      console.error('Failed to sync to Qdrant:', error);
      alert('Failed to sync to Qdrant');
    } finally {
      setSyncLoading(false);
    }
  };


  const addPayload = async () => {
    const collectionName = newPayload.collection_name || '';
    const title = newPayload.title || '';
    const description = newPayload.description || '';
    const url = newPayload.url || '';

    if (!collectionName.trim()) {
      alert('Collection name is required');
      return;
    }

    if (!title.trim() || !description.trim() || !url.trim()) {
      alert('Title, Description, and URL are required');
      return;
    }

    setAddingPayload(true);
    try {
      const payloadObj = {
        title: title,
        description: description,
        url: url
      };

      const res = await fetch(`${API_BASE}/content/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_id: newPayload.source_id || null,
          collection_name: collectionName,
          payload: payloadObj,
        }),
      });
      if (!res.ok) throw new Error('Failed to add payload');

      setNewPayload({ source_id: '', collection_name: '', title: '', description: '', url: '' });
      loadPayloads();
      alert('Payload added successfully!');
    } catch (error) {
      console.error('Failed to add payload:', error);
      alert('Failed to add payload');
    } finally {
      setAddingPayload(false);
    }
  };

  const deletePayload = async (id) => {
    if (!window.confirm('Are you sure you want to delete this payload? It will also be removed from Qdrant.')) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/content/${id}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to delete payload');
      loadPayloads();
    } catch (error) {
      console.error('Failed to delete payload:', error);
      alert('Failed to delete payload');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;

    setIsLoading(true);
    const userMessage = { sender: 'user', text: prompt };
    setMessages(prevMessages => [...prevMessages, userMessage]);

    try {
      const res = await fetch(`${API_BASE}/content/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: settings.llama_model || 'llama3:latest',
          prompt: prompt,
          collection_name: settings.default_collection_name || 'content',
        }),
        signal: AbortSignal.timeout(60000),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      setMessages(prevMessages => [...prevMessages, { sender: 'model', text: '' }]);

      if (!res.body) {
        throw new Error('Response body is null');
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        try {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.trim()) {
              try {
                const parsed = JSON.parse(line);
                if (parsed.response) {
                  setMessages(prev => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1].text += parsed.response;
                    return newMessages;
                  });
                }
              } catch (error) {
                console.error("Failed to parse JSON chunk:", line, error);
              }
            }
          }
        } catch (streamError) {
          console.error("Stream reading error:", streamError);
          break;
        }
      }

    } catch (error) {
      console.error("Failed to fetch:", error);
      let errorMessage = `Error: ${error.message}`;

      if (error.name === 'AbortError') {
        errorMessage = 'Request timed out. Please try again.';
      }

      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].text = errorMessage;
        return newMessages;
      });
    } finally {
      setIsLoading(false);
      setPrompt('');
    }
  };

  const tabs = [
    { id: 'chat', label: 'Chat', icon: ChatIcon },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
    { id: 'context', label: 'Context Browser', icon: DatabaseIcon },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content */}
      <div className={`flex-1 flex flex-col overflow-hidden ${sidebarOpen ? 'ml-64' : 'ml-0'} transition-all duration-200`}>
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-xl font-semibold text-gray-800">
              {activeTab === 'chat' && 'Chat'}
              {activeTab === 'settings' && 'Settings'}
              {activeTab === 'context' && 'Context Browser'}
            </h1>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6 bg-gray-50">
          {/* Chat Tab */}
{activeTab === 'chat' && (
  <div className="flex flex-col h-[calc(100vh-8rem)]">
    <div className="flex-1 overflow-y-auto backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6 mb-4 space-y-4">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <ChatIcon />
            <p className="mt-4 text-slate-400 text-lg">Start a conversation...</p>
          </div>
        </div>
      ) : (
        messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-2xl px-4 py-3 ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-700/50 text-slate-200'
              }`}
            >
              {msg.sender === 'user' ? (
                <p className="font-medium">{msg.text}</p>
              ) : (
                <pre className="whitespace-pre-wrap font-sans">{msg.text || 'Thinking...'}</pre>
              )}
            </div>
          </div>
        ))
      )}
    </div>

    <form onSubmit={handleSubmit} className="flex space-x-3">
      <input
        type="text"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Type your message..."
        className="flex-1 px-4 py-3 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        disabled={isLoading}
      />
      <button
        type="submit"
        disabled={isLoading || !prompt.trim()}
        className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-all duration-200 flex items-center space-x-2 shadow-lg shadow-indigo-500/50 hover:shadow-xl hover:shadow-indigo-500/50"
      >
        {isLoading ? <LoadingSpinner /> : <SendIcon />}
        <span>{isLoading ? 'Sending...' : 'Send'}</span>
      </button>
    </form>
  </div>
)}


        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white flex items-center space-x-2">
                  <SettingsIcon />
                  <span>Settings</span>
                </h2>
                {saveSuccess && (
                  <div className="flex items-center space-x-2 text-green-400">
                    <SaveIcon />
                    <span className="text-sm font-medium">Saved!</span>
                  </div>
                )}
              </div>

              {settingsLoading && (
                <div className="flex items-center justify-center py-12">
                  <LoadingSpinner />
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Ollama URL
                  </label>
                  <input
                    type="text"
                    value={settingsEditing.ollama_url || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, ollama_url: e.target.value})}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Default Collection Name
                  </label>
                  <input
                    type="text"
                    value={settingsEditing.default_collection_name || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, default_collection_name: e.target.value})}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Vector Size
                  </label>
                  <input
                    type="number"
                    value={settingsEditing.vector_size || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, vector_size: e.target.value})}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Llama Model
                  </label>
                  <input
                    type="text"
                    value={settingsEditing.llama_model || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, llama_model: e.target.value})}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Qdrant Host
                  </label>
                  <input
                    type="text"
                    value={settingsEditing.qdrant_host || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, qdrant_host: e.target.value})}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Qdrant Port
                  </label>
                  <input
                    type="number"
                    value={settingsEditing.qdrant_port || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, qdrant_port: e.target.value})}
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    RAG Context Template <span className="text-xs text-slate-500">(use {'{prompt}'} and {'{content_list}'})</span>
                  </label>
                  <textarea
                    value={settingsEditing.rag_context_template || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, rag_context_template: e.target.value})}
                    rows="4"
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    RAG Context When Search Failed <span className="text-xs text-slate-500">(use {'{prompt}'})</span>
                  </label>
                  <textarea
                    value={settingsEditing.rag_context_search_failed || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, rag_context_search_failed: e.target.value})}
                    rows="3"
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    RAG Context When No Results <span className="text-xs text-slate-500">(use {'{prompt}'})</span>
                  </label>
                  <textarea
                    value={settingsEditing.rag_context_no_results || ''}
                    onChange={(e) => setSettingsEditing({...settingsEditing, rag_context_no_results: e.target.value})}
                    rows="3"
                    className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
                  />
                </div>
              </div>

              <button
                onClick={saveSettings}
                disabled={settingsLoading}
                className="mt-6 w-full px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg shadow-indigo-500/50"
              >
                {settingsLoading ? <LoadingSpinner /> : <SaveIcon />}
                <span>Save Settings</span>
              </button>
            </div>
          </div>
        )}

        {/* Context Browser Tab */}
        {activeTab === 'context' && (
          <div className="space-y-6">
            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={syncToQdrant}
                disabled={syncLoading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-all duration-200 flex items-center space-x-2"
              >
                {syncLoading ? <LoadingSpinner /> : <SyncIcon />}
                <span>{syncLoading ? 'Syncing...' : 'Sync to Qdrant'}</span>
              </button>
              <button
                onClick={loadPayloads}
                disabled={payloadsLoading}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-all duration-200 flex items-center space-x-2"
              >
                <RefreshIcon />
                <span>Refresh</span>
              </button>
            </div>

            {/* Add Payload Section */}
            <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6">
              <h3 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
                <PlusIcon />
                <span>Add New Payload</span>
              </h3>
              <div className="space-y-4">
                {addingPayload && (
                  <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 flex items-center space-x-2 text-blue-400">
                    <LoadingSpinner />
                    <span className="text-sm font-medium">Adding payload...</span>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input
                    type="text"
                    placeholder="Source ID (optional)"
                    value={newPayload.source_id || ''}
                    onChange={(e) => setNewPayload({...newPayload, source_id: e.target.value})}
                    disabled={addingPayload}
                    className="px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <input
                    type="text"
                    placeholder="Collection Name *"
                    value={newPayload.collection_name || ''}
                    onChange={(e) => setNewPayload({...newPayload, collection_name: e.target.value})}
                    disabled={addingPayload}
                    required
                    className="px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>
                <div className="grid grid-cols-1 gap-4">
                  <input
                    type="text"
                    placeholder="Title *"
                    value={newPayload.title || ''}
                    onChange={(e) => setNewPayload({...newPayload, title: e.target.value})}
                    disabled={addingPayload}
                    required
                    className="px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <textarea
                    placeholder="Description *"
                    value={newPayload.description || ''}
                    onChange={(e) => setNewPayload({...newPayload, description: e.target.value})}
                    disabled={addingPayload}
                    required
                    rows="3"
                    className="px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed resize-none"
                  />
                  <input
                    type="url"
                    placeholder="URL *"
                    value={newPayload.url || ''}
                    onChange={(e) => setNewPayload({...newPayload, url: e.target.value})}
                    disabled={addingPayload}
                    required
                    className="px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>
                <button
                  onClick={addPayload}
                  disabled={!(newPayload.collection_name || '').trim() || !(newPayload.title || '').trim() || !(newPayload.description || '').trim() || !(newPayload.url || '').trim() || addingPayload}
                  className="w-full px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50 text-white rounded-lg font-medium transition-all duration-200 flex items-center justify-center space-x-2"
                >
                  {addingPayload ? (
                    <>
                      <LoadingSpinner />
                      <span>Adding Payload...</span>
                    </>
                  ) : (
                    <>
                      <PlusIcon />
                      <span>Add Payload</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Payloads List */}
            <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6">
              <h3 className="text-xl font-bold text-white mb-4">
                Payloads <span className="text-slate-400 font-normal">({payloads.length})</span>
              </h3>
              {payloadsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <LoadingSpinner />
                </div>
              ) : payloads.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <DatabaseIcon />
                  <p className="mt-4">No payloads found.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {payloads.map((payload) => (
                    <div
                      key={payload.id}
                      className="bg-slate-700/30 rounded-xl border border-slate-600/50 p-4 hover:border-slate-500 transition-all"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex flex-wrap items-center gap-3">
                          <span className="px-3 py-1 bg-indigo-600/20 text-indigo-300 rounded-lg text-sm font-medium">
                            ID: {payload.id}
                          </span>
                          {payload.source_id && (
                            <span className="px-3 py-1 bg-slate-600/50 text-slate-300 rounded-lg text-sm">
                              Source: {payload.source_id}
                            </span>
                          )}
                          {payload.collection_name && (
                            <span className="px-3 py-1 bg-purple-600/20 text-purple-300 rounded-lg text-sm">
                              Collection: {payload.collection_name}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => deletePayload(payload.id)}
                          className="p-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-all"
                          title="Delete"
                        >
                          <TrashIcon />
                        </button>
                      </div>
                      <pre className="bg-slate-900/50 rounded-lg p-4 overflow-x-auto text-sm text-slate-300 font-mono">
                        {JSON.stringify(payload.payload, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
         </main>
    </div>
  </div>
  );
}


export default App;
