import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import "./ChatWindow.css";


const ChatWindow = ({ user, activeSession }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const messagesEndRef = useRef(null); // Create a ref for the messages container

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


  // Auto-scroll effect when messages update
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollTo({
        top: messagesEndRef.current.scrollHeight,
        behavior: "smooth", //Smooth scrolling effect
      });
    }
  }, [messages]); // Runs every time messages change
  
  const sendMessage = async () => {
    if (!input.trim()) {
      setErrorMessage("Cannot send an empty message.");
      return;
    }
  
    if (!activeSession) {
      setErrorMessage("No session is active. Please select or create a session.");
      return;
    }
  
    // Step 1: Show user message immediately
    const newMessage = { role: "user", content: input };
    setMessages((prevMessages) => [...prevMessages, newMessage]);
    setInput(""); // Clear input field right away
  
    try {
      const token = await user.getIdToken();
  
      // Step 2: Fetch AI response
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/chat/respond`,
        { session_id: activeSession, message: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );
  
      // Step 3: Add AI response to chat window
      const botResponse = { role: "assistant", content: response.data.message };
      setMessages((prevMessages) => [...prevMessages, botResponse]);
    } catch (err) {
      setErrorMessage("Failed to send the message.");
      console.error(err);
    }
  };
  

  return (
    <div className="chat-window">

      {errorMessage && (
        <div className="error-banner">
          <span>{errorMessage}</span>
          <button className="close-error" onClick={() => setErrorMessage("")}>&times;</button>
        </div>
      )}
      
      <div className="messages" ref={messagesEndRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            {msg.content}
          </div>
          
        ))}
      </div>
      
      <div className="chat-input">
        <input type="text" placeholder="Type a message..." value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault(); // Prevents a new line from being added
              sendMessage();
            }
          }}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
      
    </div>
  );
};

export default ChatWindow;
