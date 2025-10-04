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
      console.log('Sending request with prompt:', prompt);
      const res = await fetch('http://localhost:8000/api/v1/products/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'llama3.2:1b',
          prompt: prompt,
        }),
      });

      console.log('Response status:', res.status);
      console.log('Response headers:', res.headers);

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
      let chunkCount = 0;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('Stream completed, total chunks:', chunkCount);
          break;
        }
        
        chunkCount++;
        console.log('Received chunk:', chunkCount, 'size:', value.length);
        
        // Decode the chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });
        
        // Process complete lines from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer
        
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