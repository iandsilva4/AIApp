import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./ChatSidebar.css";
import { ReactComponent as NewChatIcon } from '../assets/new-chat-icon.svg';
import { ReactComponent as SidebarToggleIcon } from '../assets/sidebar-toggle-icon.svg';
import { ReactComponent as EditIcon } from '../assets/edit-icon.svg';
import '../styles/shared.css';

const getTimeDisplay = (timestamp) => {
  if (!timestamp) return "No messages yet...";
  
  // Explicitly parse the UTC timestamp and convert to local time
  const date = new Date(timestamp + 'Z'); // Adding 'Z' ensures we parse as UTC
  const now = new Date();


  // Format the full timestamp for hover using local timezone
  const fullTimestamp = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone // Use user's timezone
  }).format(date);

  return { relative: fullTimestamp, full: fullTimestamp };
};

const ChatSidebar = ({ user, activeSession, setActiveSession, setIsSidebarOpen, sessions, setSessions }) => {
  const [newTitle, setNewTitle] = useState("");
  const [isNamingSession, setIsNamingSession] = useState(false);
  const [error, setError] = useState("");
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [openSection, setOpenSection] = useState('active'); // 'active', 'archived', or null

  // Fetch existing sessions
  const fetchSessions = useCallback(async () => {
    if (!user) return;
    try {
      const token = await user.getIdToken();
      const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSessions(response.data);
    } catch (err) {
      setError("Failed to load sessions.");
      console.error("Error fetching sessions:", err);
    }
  }, [user, setSessions]);

  // Add this effect to refresh sessions when activeSession changes
  useEffect(() => {
    if (user) {
      fetchSessions();
    }
  }, [fetchSessions, user, activeSession]); // Add activeSession as dependency

  // Create a new session
  const handleCreateSession = async () => {
    if (!newTitle.trim()) {
      setError("Please enter a session title.");
      return;
    }

    try {
      const token = await user.getIdToken();
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/sessions`,
        { title: newTitle },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions([response.data, ...sessions]);
      setActiveSession(response.data.id);
      setIsNamingSession(false);
      setNewTitle("");
    } catch (err) {
      setError("Failed to create a new session.");
      console.error("Error creating session:", err.response ? err.response.data : err.message);
    }
  };

  const handleUpdateSession = async (id, title) => {
    try {
      const token = await user.getIdToken();
      const response = await axios.put(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${id}`,
        { title },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions(sessions.map(session =>
        session.id === id ? response.data : session
      ));
      setEditingSessionId(null);
      setNewTitle("");
    } catch (err) {
      setError("Failed to update the session.");
      console.error("Error updating session:", err.response ? err.response.data : err.message);
    }
  };

  // Add delete handler function
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    
    // Add confirmation dialog
    if (!window.confirm("Are you sure you want to delete this chat?")) {
      return;
    }

    try {
      const token = await user.getIdToken();
      await axios.delete(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${sessionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Remove session from state
      setSessions(sessions.filter(s => s.id !== sessionId));
      
      // If the deleted session was active, clear active session
      if (sessionId === activeSession) {
        setActiveSession(null);
      }
    } catch (err) {
      setError("Failed to delete session.");
      console.error("Error deleting session:", err);
    }
  };

  // Add archive handler function
  const handleArchiveSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      const token = await user.getIdToken();
      const response = await axios.put(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${sessionId}/archive`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Update session in state with the response data
      setSessions(sessions.map(s => 
        s.id === sessionId ? response.data : s
      ));
      
      // If the archived session was active, clear active session
      if (sessionId === activeSession) {
        setActiveSession(null);
      }
    } catch (err) {
      setError("Failed to archive session.");
      console.error("Error archiving session:", err);
    }
  };

  // Add useEffect for error handling
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError("");
      }, 3000); // Error disappears after 3 seconds

      // Cleanup timeout on component unmount or when error changes
      return () => clearTimeout(timer);
    }
  }, [error]);

  // Update the click handler for section headers
  const handleSectionToggle = (section) => {
    if (openSection === section) {
      setOpenSection(null);
    } else {
      setOpenSection(section);
    }
  };

  return (
    <>
      {/* Sidebar - Fully disappears when closed */}
      <div className="chat-sidebar">
        <div className="chat-sidebar-header">
          <div className="header-title">
            <span>Chats</span>
          </div>
          
          <div className = "header-button-section">
            <button className="icon-button" onClick={() => setIsSidebarOpen(false)}>
              <SidebarToggleIcon />
            </button>
            <button className="icon-button" onClick={async () => {
              try {
                // End current session if one exists
                if (activeSession) {
                  const token = await user.getIdToken();
                  await axios.put(
                    `${process.env.REACT_APP_BACKEND_URL}/sessions/${activeSession}/end`,
                    {},
                    { headers: { Authorization: `Bearer ${token}` } }
                  );
                  
                  // Update the ended session in the list
                  setSessions(prevSessions => 
                    prevSessions.map(session => 
                      session.id === activeSession ? { ...session, is_ended: true } : session
                    )
                  );
                }

                // Create new session
                const token = await user.getIdToken();
                const response = await axios.post(
                  `${process.env.REACT_APP_BACKEND_URL}/sessions`,
                  { title: "Untitled Chat" },
                  { headers: { Authorization: `Bearer ${token}` } }
                );

                setSessions([response.data, ...sessions]);
                setActiveSession(response.data.id);
              } catch (err) {
                setError("Failed to create a new session.");
                console.error("Error creating session:", err);
              }
            }}>
              <NewChatIcon />
            </button>
          </div>
        </div>

        {error && (
          <div className="error-message fade-out">
            {error}
          </div>
        )}

        {/* Add new session input form */}
        {isNamingSession && (
          <div className="new-session-input">
            <div className="new-session-title-input">
              <input
                type="text"
                placeholder="Enter session title"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateSession();
                  }
                  if (e.key === 'Escape') {
                    setIsNamingSession(false);
                    setNewTitle("");
                  }
                }}
                autoFocus
              />
            </div>
            <div className="new-session-sub-buttons">
              <button className="create-button" onClick={handleCreateSession}>Create</button>
              <button className="cancel-button" onClick={() => {
                setIsNamingSession(false);
                setNewTitle("");
              }}>Cancel</button>
            </div>
          </div>
        )}

        <div className="lists-container">
          <div className="active-sessions">
            <div className="chat-sidebar-section active-section-header"
              onClick={() => handleSectionToggle('active')}>
              <span>YOUR SESSIONS ({sessions.filter(s => !s.is_archived).length})</span>
              <span className={`section-toggle ${openSection === 'active' ? 'open' : ''}`}>▼</span>
            </div>
            <ul className={`session-list ${openSection !== 'active' ? 'collapsed' : ''}`}>
              {sessions
                .filter(s => !s.is_archived)
                .map((session) => (
                  <li
                    key={session.id}
                    className={`session-item ${session.id === activeSession ? "active" : ""}`}
                    onClick={() => !session.isNew && setActiveSession(session.id)}
                  >
                    {!session.isNew && (
                      <>
                        <div className="session-header">
                          {editingSessionId === session.id ? (
                            <div className="edit-input-container">
                              <input
                                type="text"
                                className="session-edit-input"
                                value={newTitle}
                                onChange={(e) => setNewTitle(e.target.value)}
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter' && newTitle.trim()) {
                                    handleUpdateSession(session.id, newTitle);
                                  }
                                  if (e.key === 'Escape') {
                                    setEditingSessionId(null);
                                    setNewTitle('');
                                  }
                                }}
                                onClick={(e) => e.stopPropagation()}
                              />
                              <div className="edit-actions">
                                <button 
                                  className="save-button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (newTitle.trim()) {
                                      handleUpdateSession(session.id, newTitle);
                                    }
                                  }}
                                  title="Save"
                                >
                                  ✓
                                </button>
                                <button 
                                  className="cancel-button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setEditingSessionId(null);
                                    setNewTitle('');
                                  }}
                                  title="Cancel"
                                >
                                  ✕
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className={`session-title ${session.is_ended ? 'ended' : ''}`}>
                                {session.title}
                                {session.is_ended && <span className="ended-badge">Ended</span>}
                              </div>
                              <div className="session-actions">
                                <button 
                                  className="edit-button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setEditingSessionId(session.id);
                                    setNewTitle(session.title);
                                  }}
                                  title="Edit chat name"
                                >
                                  <EditIcon />
                                </button>
                                <button 
                                  className="archive-button"
                                  onClick={(e) => handleArchiveSession(e, session.id)}
                                  title="Archive chat"
                                >
                                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M21 8v13H3V8M1 3h22v5H1V3zM10 12h4" />
                                  </svg>
                                </button>
                                <button 
                                  className="delete-button"
                                  onClick={(e) => handleDeleteSession(e, session.id)}
                                  title="Delete chat"
                                >
                                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                                  </svg>
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                        <div className="session-preview">
                          {session.messages?.length > 0 ? (
                            <>
                              <span className="preview-text">
                                {session.preview || "Empty conversation"}
                              </span>
                              <span 
                                className="timestamp" 
                                title={getTimeDisplay(session.timestamp).full}
                              >
                                {getTimeDisplay(session.timestamp).relative}
                              </span>
                            </>
                          ) : (
                            <span className="timestamp">No messages yet...</span>
                          )}
                        </div>
                      </>
                    )}
                  </li>
                ))}
            </ul>
          </div>

          {sessions.some(s => s.is_archived) && (
            <div className="archived-sessions">
              <div className="chat-sidebar-section archived-section-header"
                onClick={() => handleSectionToggle('archived')}>
                <span>ARCHIVED ({sessions.filter(s => s.is_archived).length})</span>
                <span className={`section-toggle ${openSection === 'archived' ? 'open' : ''}`}>▼</span>
              </div>
              <ul className={`session-list ${openSection !== 'archived' ? 'collapsed' : ''}`}>
                {sessions
                  .filter(s => s.is_archived)
                  .map((session) => (
                    <li
                      key={session.id}
                      className={`session-item archived ${session.id === activeSession ? "active" : ""}`}
                      onClick={() => !session.isNew && setActiveSession(session.id)}
                    >
                      {!session.isNew && (
                        <>
                          <div className="session-header">
                            {editingSessionId === session.id ? (
                              <div className="edit-input-container">
                                <input
                                  type="text"
                                  className="session-edit-input"
                                  value={newTitle}
                                  onChange={(e) => setNewTitle(e.target.value)}
                                  autoFocus
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter' && newTitle.trim()) {
                                      handleUpdateSession(session.id, newTitle);
                                    }
                                    if (e.key === 'Escape') {
                                      setEditingSessionId(null);
                                      setNewTitle('');
                                    }
                                  }}
                                  onClick={(e) => e.stopPropagation()}
                                />
                                <div className="edit-actions">
                                  <button 
                                    className="save-button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      if (newTitle.trim()) {
                                        handleUpdateSession(session.id, newTitle);
                                      }
                                    }}
                                    title="Save"
                                  >
                                    ✓
                                  </button>
                                  <button 
                                    className="cancel-button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditingSessionId(null);
                                      setNewTitle('');
                                    }}
                                    title="Cancel"
                                  >
                                    ✕
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <>
                                <div className={`session-title ${session.is_ended ? 'ended' : ''}`}>
                                  {session.title}
                                  {session.is_ended && <span className="ended-badge">Ended</span>}
                                </div>
                                <div className="session-actions">
                                  <button 
                                    className="edit-button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditingSessionId(session.id);
                                      setNewTitle(session.title);
                                    }}
                                    title="Edit chat name"
                                  >
                                    <EditIcon />
                                  </button>
                                  <button 
                                    className="unarchive-button"
                                    onClick={(e) => handleArchiveSession(e, session.id)}
                                    title="Unarchive chat"
                                  >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                      <path d="M21 8v13H3V8M1 3h22v5H1V3zM10 12h4M12 10v4" />
                                    </svg>
                                  </button>
                                  <button 
                                    className="delete-button"
                                    onClick={(e) => handleDeleteSession(e, session.id)}
                                    title="Delete chat"
                                  >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                                    </svg>
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                          <div className="session-preview">
                            {session.messages?.length > 0 ? (
                              <>
                                <span className="preview-text">
                                  {session.preview || "Empty conversation"}
                                </span>
                                <span 
                                  className="timestamp" 
                                  title={getTimeDisplay(session.timestamp).full}
                                >
                                  {getTimeDisplay(session.timestamp).relative}
                                </span>
                              </>
                            ) : (
                              <span className="timestamp">No messages yet...</span>
                            )}
                          </div>
                        </>
                      )}
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </>
  );
}  

export default ChatSidebar;