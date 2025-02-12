import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import "./ChatWindow.css";
import assistantIcon from '../assets/assistant-icon.svg'; // You'll need to add this icon
import defaultUserIcon from '../assets/default-user-icon.svg';
import { ReactComponent as SidebarToggleIcon } from '../assets/sidebar-toggle-icon.svg';
import { ReactComponent as SendIcon } from '../assets/send-icon.svg';
import '../styles/shared.css';


const ChatWindow = ({ user, activeSession, isSidebarOpen, setIsSidebarOpen  }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [sessionInputs, setSessionInputs] = useState({}); // Store inputs per session
  const prevSessionRef = useRef(activeSession); // Track previous session
  const messagesEndRef = useRef(null); // Create a ref for the messages container
  const textareaRef = useRef(null); // Add ref for textarea
  const [isLoading, setIsLoading] = useState(false);
  const [isAIResponding, setIsAIResponding] = useState(false);

  // Reset textarea height
  const resetTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '52px'; // Match min-height from CSS
    }
  };

  // Handle session switching
  useEffect(() => {
    if (prevSessionRef.current !== activeSession) {
      // Save input from previous session
      if (prevSessionRef.current) {
        setSessionInputs(prev => ({
          ...prev,
          [prevSessionRef.current]: input
        }));
      }

      // Load input for new session
      if (activeSession) {
        setInput(sessionInputs[activeSession] || "");
        // Use setTimeout to ensure the textarea is available after state update
        setTimeout(() => {
          if (textareaRef.current) {
            textareaRef.current.style.height = '52px';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
          }
        }, 0);
      } else {
        setInput("");
        resetTextareaHeight();
      }

      prevSessionRef.current = activeSession;
    }
  }, [activeSession, input, sessionInputs]);

  // Memoize the fetchMessages function
  const fetchMessages = useCallback(async () => {
    if (!activeSession || !user) return;
    setIsLoading(true);
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
    } finally {
      setIsLoading(false);
    }
  }, [user, activeSession]);

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

    const userMessage = { role: "user", content: input };
    
    // Immediately add user message to the chat
    setMessages(prevMessages => [...prevMessages, userMessage]);
  
    // Clear the input and its stored value for this session
    setInput("");
    setSessionInputs(prev => ({
      ...prev,
      [activeSession]: ""
    }));
    resetTextareaHeight();
  
    try {
      setIsAIResponding(true); // Show loading state
      const token = await user.getIdToken();
  
      // Add temporary loading message
      setMessages(prevMessages => [...prevMessages, 
        { role: "assistant", content: "...", isLoading: true }
      ]);

      // Fetch AI response
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/chat/respond`,
        { session_id: activeSession, message: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );
  
      // Replace loading message with actual response
      setMessages(prevMessages => 
        prevMessages.slice(0, -1).concat({ 
          role: "assistant", 
          content: response.data.message 
        })
      );
    } catch (err) {
      setErrorMessage("Failed to send the message.");
      console.error(err);
      // Remove loading message on error
      setMessages(prevMessages => prevMessages.slice(0, -1));
    } finally {
      setIsAIResponding(false);
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

  // Reset height when active session changes
  useEffect(() => {
    resetTextareaHeight();
  }, [activeSession]);

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
          {isLoading ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Loading messages...</p>
            </div>
          ) : (
            messages.map((msg, index) => (
              msg.role === 'assistant' ? (
                <div key={index} className="message-container assistant">
                  <div className="profile-icon assistant">
                    <img src={assistantIcon} alt="Assistant" />
                  </div>
                  <div className={`message ${msg.role} ${msg.isLoading ? 'loading' : ''}`}>
                    {msg.isLoading ? (
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    ) : (
                      msg.content
                    )}
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
            ))
          )}
        </div>
        
        <div className="chat-input">
          <div className="input-container">
            <textarea 
              ref={textareaRef}
              placeholder="Type a message..." 
              value={input} 
              onChange={(e) => {
                e.target.style.height = '52px'; // Reset to min-height first
                e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                setInput(e.target.value);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              rows="1"
            />
            <div className="send-button-container">
              <button onClick={sendMessage} className="send-button">
                <SendIcon />
              </button>
            </div>
          </div>
        </div>
        
    </div>
  );
};

export default ChatWindow;
