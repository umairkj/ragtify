import React, { useState } from 'react';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;

    setIsLoading(true);

    const userMessage = { sender: 'user', text: prompt };
    setMessages(prevMessages => [...prevMessages, userMessage]);

    try {
      const res = await fetch('http://localhost:8000/api/v1/products/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'llama3',
          prompt: prompt,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      setMessages(prevMessages => [...prevMessages, { sender: 'model', text: '' }]);
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const jsonChunks = chunk.split('\n').filter(c => c.trim() !== '');

        for (const jsonChunk of jsonChunks) {
            try {
                const parsed = JSON.parse(jsonChunk);
                if (parsed.response) {
                    setMessages(prev => {
                      const newMessages = [...prev];
                      newMessages[newMessages.length - 1].text += parsed.response;
                      return newMessages;
                    });
                }
            } catch (error) {
                console.error("Failed to parse JSON chunk:", jsonChunk, error);
            }
        }
      }

    } catch (error) {
      console.error("Failed to fetch:", error);
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].text = `Error: ${error.message}`;
        return newMessages;
      });
    } finally {
      setIsLoading(false);
      setPrompt('');
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Chat with Llama</h1>
      </header>
      <main className="App-main">
        <div className="chat-window">
          {messages.length > 0 ? messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender}`}>
              {msg.sender === 'user' ? (
                <strong>{msg.text}</strong>
              ) : (
                <pre>{msg.text}</pre>
              )}
            </div>
          )) : <div className="placeholder">Ask me anything...</div>}
        </div>
        <form onSubmit={handleSubmit} className="chat-form">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Type your message here..."
            className="chat-input"
            disabled={isLoading}
          />
          <button type="submit" className="send-button" disabled={isLoading}>
            {isLoading ? 'Thinking...' : 'Send'}
          </button>
        </form>
      </main>
    </div>
  );
}

export default App; 