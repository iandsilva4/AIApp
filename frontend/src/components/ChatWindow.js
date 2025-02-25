import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import "./ChatWindow.css";
import defaultUserIcon from '../assets/default-user-icon.svg';
import { ReactComponent as SidebarToggleIcon } from '../assets/sidebar-toggle-icon.svg';
import { ReactComponent as SendIcon } from '../assets/send-icon.svg';
import { ReactComponent as EndIcon } from '../assets/end-icon.svg';
import '../styles/shared.css';
import ReactMarkdown from 'react-markdown';


const ChatWindow = ({ user, activeSession, isSidebarOpen, setIsSidebarOpen, sessions, setSessions, setActiveSession, isCreatingNewSession }) => {
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
  const [currentAssistant, setCurrentAssistant] = useState(null);
  const [availableAssistants, setAvailableAssistants] = useState([]);
  const [availableGoals, setAvailableGoals] = useState([]);
  const [isInitializingChat, setIsInitializingChat] = useState(false);
  const [initializationSteps, setInitializationSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState('');

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

    // Find the current session data
    const currentSession = sessions.find(s => s.id === activeSession);
    if (!currentSession) {
      setErrorMessage("Session data not found.");
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
        { 
          session_id: activeSession, 
          message: input,
          assistant_id: currentSession.assistant_id,
          goal_ids: currentSession.goal_ids
        },
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
  const getCurrentSession = useCallback(() => {
    return sessions.find(s => s.id === activeSession);
  }, [sessions, activeSession]);

  // Update current assistant when session changes
  useEffect(() => {
    const session = getCurrentSession();
    if (session) {
      setCurrentAssistant(session);
      console.log("Current assistant state:", {
        assistant_id: session.assistant_id,
        assistant_name: session.assistant_name
      });
    }
  }, [activeSession, sessions, getCurrentSession]);

  // Update the assistants fetch useEffect
  useEffect(() => {
    const fetchAssistants = async (retryCount = 0) => {
      if (!user) return;
      
      try {
        const token = await user.getIdToken();
        const response = await axios.get(
          `${process.env.REACT_APP_BACKEND_URL}/assistants`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setAvailableAssistants(response.data);
      } catch (error) {
        console.error("Failed to fetch assistants:", error);
        
        // If we get a 401 and haven't exceeded retries, try again after a delay
        if (error.response?.status === 401 && retryCount < 3) {
          console.log(`Retrying fetch assistants (attempt ${retryCount + 1})...`);
          setTimeout(() => {
            fetchAssistants(retryCount + 1);
          }, 1000);
        } else {
          setErrorMessage("Failed to load assistants");
        }
      }
    };

    if (user) {
      // Add small initial delay to allow Firebase to fully initialize
      setTimeout(() => {
        fetchAssistants();
      }, 500);
    }
  }, [user]);

  // Update the goals fetch useEffect
  useEffect(() => {
    const fetchGoals = async (retryCount = 0) => {
      if (!user) return;
      
      try {
        const token = await user.getIdToken();
        const response = await axios.get(
          `${process.env.REACT_APP_BACKEND_URL}/goals`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setAvailableGoals(response.data);
      } catch (error) {
        console.error("Failed to fetch goals:", error);
        
        // If we get a 401 and haven't exceeded retries, try again after a delay
        if (error.response?.status === 401 && retryCount < 3) {
          console.log(`Retrying fetch goals (attempt ${retryCount + 1})...`);
          setTimeout(() => {
            fetchGoals(retryCount + 1);
          }, 1000);
        } else {
          setErrorMessage("Failed to load goals");
        }
      }
    };

    if (user) {
      // Add small initial delay to allow Firebase to fully initialize
      setTimeout(() => {
        fetchGoals();
      }, 500);
    }
  }, [user]);

  // Update the effect to also set messages
  useEffect(() => {
    const initializeNewChat = async () => {
      if (!activeSession || isInitializingChat) return;
      
      const session = sessions.find(s => s.id === activeSession);
      if (!session || session.messages?.length > 0) return;
      
      try {
        setIsInitializingChat(true);
        const token = await user.getIdToken();

        setCurrentStep('Ending old sessions');

        // First, end old sessions
        const createResponse = await axios.post(
          `${process.env.REACT_APP_BACKEND_URL}/sessions`,
          { session_id: activeSession },
          { headers: { Authorization: `Bearer ${token}` } }
        );

        // Fetch all sessions to ensure sidebar is up to date after ending old sessions
        const sessionsResponse = await axios.get(
          `${process.env.REACT_APP_BACKEND_URL}/sessions`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setSessions(sessionsResponse.data);

        setInitializationSteps(prev => [...prev, 'Ending old sessions']);
        setCurrentStep('Gathering History');

        // Then get initial AI response
        const initResponse = await axios.post(
          `${process.env.REACT_APP_BACKEND_URL}/chat/respond`,
          { 
            session_id: activeSession,
            is_initial: true,
            assistant_id: session.assistant_id,
            goal_ids: session.goal_ids
          },
          { headers: { Authorization: `Bearer ${token}` } }
        );

        // Update messages with AI's initial response
        const newMessages = initResponse.data.messages;
        setMessages(newMessages);
        
        setSessions(prevSessions => 
          prevSessions.map(s => 
            s.id === activeSession
              ? { ...createResponse.data, messages: newMessages }
              : s
          )
        );

        setInitializationSteps([]);
        setCurrentStep('');

      } catch (err) {
        setErrorMessage("Failed to initialize chat");
        console.error("Error initializing chat:", err);
      } finally {
        setIsInitializingChat(false);
      }
    };

    initializeNewChat();
  }, [activeSession, user, sessions, isInitializingChat, setSessions]);

  // Replace the existing renderStartingNewChat function with this updated version
  const renderStartingNewChat = () => (
    <div className="welcome-message assistants-grid">
      {(!user || (!availableAssistants.length && !availableGoals.length)) ? (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading...</p>
        </div>
      ) : (
        <>
          <h2>Coaches</h2>
          <div className="assistants-list">
            {availableAssistants.map((assistant) => (
              <div key={assistant.id} className="assistant-card">
                <div className="assistant-avatar">
                  {assistant.avatar_url ? (
                    <img src={assistant.avatar_url} alt={assistant.name} />
                  ) : (
                    <div className="assistant-initial">
                      {(assistant.name?.[0] || 'A').toUpperCase()}
                    </div>
                  )}
                </div>
                <h3>{assistant.name}</h3>
                <p>{assistant.short_desc}</p>
              </div>
            ))}
            {availableAssistants.length === 0 && (
              <div className="loading-spinner"></div>
            )}
          </div>

          <h2>Goals</h2>
          <div className="assistants-list">
            {availableGoals
              .sort((a, b) => a.id === 1 ? 1 : b.id === 1 ? -1 : 0)
              .map((goal) => (
                <div key={goal.id} className="goal-container">
                  <div className="category-tag" data-category={goal.category?.toLowerCase().replace(/\s+/g, '-')}>
                    {goal.category}
                  </div>
                  <div className="assistant-card">
                    <div className="assistant-avatar">
                      {goal.avatar_url ? (
                        <img src={goal.avatar_url} alt={goal.name} />
                      ) : (
                        <div className="assistant-initial">
                          {(goal.name?.[0] || 'G').toUpperCase()}
                        </div>
                      )}
                    </div>
                    <h3>{goal.name}</h3>
                    <p>{goal.short_desc || "Category"}</p>
                  </div>
                </div>
              ))}
            {availableGoals.length === 0 && (
              <div className="loading-spinner"></div>
            )}
          </div>
        </>
      )}
    </div>
  );

  // Update the renderLoadingMessage to remove the initializing text
  const renderLoadingMessage = () => (
    <div className="message-container assistant">
      <div className="profile-icon assistant">
        {currentAssistant?.assistant_avatar ? (
          <img 
            src={currentAssistant.assistant_avatar} 
            alt={currentAssistant.assistant_name || 'Assistant'} 
            className="assistant-avatar"
          />
        ) : (
          <div className="assistant-initial">
            {(currentAssistant?.assistant_name?.[0] || 'A').toUpperCase()}
          </div>
        )}
      </div>
      <div className="message assistant loading">
        {messages.length === 0 ? (
          <div className="initialization-steps">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div className="steps-list">
              {initializationSteps.map((step, index) => (
                <div key={index} className={`step completed`}>
                  {step}
                </div>
              ))}
              {currentStep && (
                <div className="step current">
                  {currentStep}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="chat-window">
      <div className="chat-header">
        {!isSidebarOpen && (
          <button className="icon-button" title="Show sidebar" onClick={() => setIsSidebarOpen(true)}>
            <SidebarToggleIcon />
          </button>
        )}
        <div className="header-title">
          <span>Chat with {currentAssistant?.assistant_name || 'a Coach'}</span>
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
        {isCreatingNewSession && user ? (
          renderStartingNewChat()
        ) : !activeSession ? (
          <div className="welcome-message">
            <h2>Welcome to your AI Coach!<span className="welcome-emoji">👋</span></h2>
            <div className="welcome-steps">
              <p>Get started in 3 simple steps:</p>
              <ol>
                <li>Click the <b>+</b> button to start a new chat</li>
                <li>Ask any question or describe what you need help with</li>
                <li>Get instant, helpful responses from your AI assistant</li>
              </ol>
              <p className="welcome-hint">Feel free to share your thoughts, feelings, or experiences. I'm here to listen, reflect, and support your journey.</p>
              <p className="welcome-hint">When you're done, end the conversation and we'll store it in memory. If you don't want us to remember it, you can archive or delete it!</p>
            </div>
          </div>
        ) : isLoading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading messages...</p>
          </div>
        ) : (
          <>
            {messages.length === 0 ? (
              renderLoadingMessage()
            ) : (
              <>
                {messages.map((msg, index) => (
                  msg.role === 'assistant' ? (
                    <div key={index} className="message-container assistant">
                      <div className="profile-icon assistant">
                        {currentAssistant?.assistant_avatar ? (
                          <img 
                            src={currentAssistant.assistant_avatar} 
                            alt={currentAssistant.assistant_name || 'Assistant'} 
                            className="assistant-avatar"
                          />
                        ) : (
                          <div className="assistant-initial">
                            {(currentAssistant?.assistant_name?.[0] || 'A').toUpperCase()}
                          </div>
                        )}
                      </div>
                      <div className={`message ${msg.role} ${msg.isLoading ? 'loading' : ''}`}>
                        {msg.isLoading && index === messages.length - 1 ? (
                          <div className="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                        ) : (
                          <>
                            {currentAssistant && (
                              <div className="assistant-name">
                                {currentAssistant.assistant_name || 'AI Assistant'}
                              </div>
                            )}
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                          </>
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
                      {currentAssistant?.assistant_avatar ? (
                        <img 
                          src={currentAssistant.assistant_avatar} 
                          alt={currentAssistant.assistant_name || 'Assistant'} 
                          className="assistant-avatar"
                        />
                      ) : (
                        <div className="assistant-initial">
                          {(currentAssistant?.assistant_name?.[0] || 'A').toUpperCase()}
                        </div>
                      )}
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