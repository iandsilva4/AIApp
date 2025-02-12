import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import "./ChatWindow.css";
import assistantIcon from '../assets/assistant-icon.svg'; // You'll need to add this icon
import defaultUserIcon from '../assets/default-user-icon.svg';
import { ReactComponent as SidebarToggleIcon } from '../assets/sidebar-toggle-icon.svg';
import '../styles/shared.css';


const ChatWindow = ({ user, activeSession, isSidebarOpen, setIsSidebarOpen  }) => {
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

  // Add function to get user initials with error handling
  const getUserInitials = () => {
    try {
      if (!user?.displayName?.trim()) return null;
      
      const names = user.displayName.trim().split(' ');
      if (names.length > 0 && names[0]) {
        return names
          .map(name => name[0])
          .join('')
          .toUpperCase()
          .slice(0, 2);
      }
      return null;
    } catch {
      return null;
    }
  };

  // Add useEffect for error handling
  useEffect(() => {
    if (errorMessage) {
      const timer = setTimeout(() => {
        setErrorMessage("");
      }, 3000); // Error disappears after 3 seconds

      // Cleanup timeout on component unmount or when error changes
      return () => clearTimeout(timer);
    }
  }, [errorMessage]);

  return (
    <div className="chat-window">
      <div className="chat-header">
        {!isSidebarOpen && (
          <button className="icon-button" onClick={() => setIsSidebarOpen(true)}>
            <SidebarToggleIcon />
          </button>
        )}
        <div className="header-title">
          <span>Chat with Ian</span>
        </div>
      </div>


        {errorMessage && (
          <div className="error-message fade-out">
            {errorMessage}
          </div>
        )}
        
        <div className="messages" ref={messagesEndRef}>
          {messages.map((msg, index) => (
            msg.role === 'assistant' ? (
              <div key={index} className="message-container assistant">
                <div className="profile-icon assistant">
                  <img src={assistantIcon} alt="Assistant" />
                </div>
                <div className={`message ${msg.role}`}>
                  {msg.content}
                </div>
              </div>
            ) : (
              <div key={index} className="message-container user">
                <div className="profile-icon user">
                  {getUserInitials() || <img src={defaultUserIcon} alt="User" />}
                </div>
                <div className={`message ${msg.role}`}>
                  {msg.content}
                </div>
              </div>
            )
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
