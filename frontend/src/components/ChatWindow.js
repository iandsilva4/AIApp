import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./ChatWindow.css";


const ChatWindow = ({ user, activeSession }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  // Memoize the fetchMessages function
  const fetchMessages = useCallback(async () => {
    if (!activeSession) return;

    try {
      const token = await user.getIdToken();
      const response = await axios.get(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${activeSession}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessages(response.data.messages || []);
    } catch (error) {
      setErrorMessage("Failed to load messages.");
      console.error(error);
    }
  }, [user, activeSession]); // Add user and activeSession to the dependency array

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]); // Add fetchMessages to the dependency array

  const sendMessage = async () => {
    if (!input.trim()) {
      setErrorMessage("Cannot send an empty message.");
      return;
    }

    if (!activeSession) {
      setErrorMessage("No session is active. Please select or create a session.");
      return;
    }

    try {
      const token = await user.getIdToken();
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/chat/respond`,
        { session_id: activeSession, message: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setMessages([...messages, { role: "user", content: input }, { role: "assistant", content: response.data.message }]);
      setInput("");
    } catch (err) {
      setErrorMessage("Failed to send the message.");
      console.error(err);
    }
  };

  return (
    <div className="chat-window">
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input type="text" placeholder="Type a message..." value={input} onChange={(e) => setInput(e.target.value)} />
        <button onClick={sendMessage}>Send</button>
      </div>
      {errorMessage && <p className="error">{errorMessage}</p>}
    </div>
  );
};

export default ChatWindow;
