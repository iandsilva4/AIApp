import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import "./ChatWindow.css";
import assistantIcon from '../assets/assistant-icon.svg'; // You'll need to add this icon
import defaultUserIcon from '../assets/default-user-icon.svg';
import { ReactComponent as SidebarToggleIcon } from '../assets/sidebar-toggle-icon.svg';
import { ReactComponent as SendIcon } from '../assets/send-icon.svg';
import { ReactComponent as EndIcon } from '../assets/end-icon.svg';
import '../styles/shared.css';
import ReactMarkdown from 'react-markdown';


const ChatWindow = ({ user, activeSession, isSidebarOpen, setIsSidebarOpen, sessions, setSessions, setActiveSession }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [sessionInputs, setSessionInputs] = useState({}); // Store inputs per session
  const prevSessionRef = useRef(activeSession); // Track previous session
  const messagesEndRef = useRef(null); // Create a ref for the messages container
  const textareaRef = useRef(null); // Add ref for textarea
  const [isLoading, setIsLoading] = useState(false);
  const [isAIResponding, setIsAIResponding] = useState(false);
  const [isEndingSession, setIsEndingSession] = useState(false);

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
      if (error.response?.status !== 404) {
        setErrorMessage("Failed to load messages.");
        console.error(error);
      } else {
        setActiveSession(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, [user, activeSession, setActiveSession]);

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

  const handleEndSession = async () => {
    if (!activeSession) return;
    
    try {
      setIsEndingSession(true);
      const token = await user.getIdToken();
      
      const endResponse = await axios.put(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${activeSession}/end`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setSessions(prevSessions => 
        prevSessions.map(session => 
          session.id === activeSession ? endResponse.data : session
        )
      );

    } catch (err) {
      setErrorMessage("Failed to end session");
      console.error("Error ending session:", err);
    } finally {
      setIsEndingSession(false);
    }
  };

  // Add helper to get current session data
  const getCurrentSession = () => {
    return sessions.find(s => s.id === activeSession);
  };

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
        {activeSession && !getCurrentSession()?.is_ended && (
          <button 
            className="icon-button end-session-button"
            onClick={handleEndSession}
            disabled={isEndingSession}
            title="End session"
          >
            {isEndingSession ? (
              <div className="button-spinner"></div>
            ) : (
              <EndIcon />
            )}
          </button>
        )}
      </div>

      {errorMessage && (
        <div className="error-message fade-out">
          {errorMessage}
        </div>
      )}
      
      <div className="messages" ref={messagesEndRef}>
        {!activeSession ? (
          <div className="welcome-message">
            <p>Welcome! Select a chat or create a new one to get started.</p>
          </div>
        ) : isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading messages...</p>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              msg.role === 'assistant' ? (
                <div key={index} className="message-container assistant">
                  <div className="profile-icon assistant">
                    <img src={assistantIcon} alt="Assistant" />
                  </div>
                  <div className={`message ${msg.role} ${msg.isLoading ? 'loading' : ''}`}>
                    {msg.isLoading && index === messages.length - 1 ? (
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    ) : (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}
                  </div>
                </div>
              ) : (
                <div key={index} className="message-container user">
                  <div className="profile-icon user">
                    {getUserInitials() || <img src={defaultUserIcon} alt="User" />}
                  </div>
                  <div className={`message ${msg.role}`}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              )
            ))}
            {isAIResponding && !messages[messages.length - 1]?.isLoading && (
              <div className="message-container assistant">
                <div className="profile-icon assistant">
                  <img src={assistantIcon} alt="Assistant" />
                </div>
                <div className="message assistant loading">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
      
      {activeSession && (
        <div className="chat-input">
          <div className="input-container">
            <textarea 
              ref={textareaRef}
              placeholder={getCurrentSession()?.is_ended ? 
                "This session has ended. Create a new session to continue chatting." : 
                "Type a message..."
              } 
              value={input} 
              onChange={(e) => {
                if (!getCurrentSession()?.is_ended) {
                  e.target.style.height = '52px';
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                  setInput(e.target.value);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !getCurrentSession()?.is_ended) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              disabled={getCurrentSession()?.is_ended}
              rows="1"
            />
            <div className="send-button-container">
              <button 
                onClick={sendMessage} 
                className={`send-button ${getCurrentSession()?.is_ended ? 'disabled' : ''}`}
                disabled={getCurrentSession()?.is_ended}
              >
                <SendIcon />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatWindow;