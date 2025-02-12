import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./ChatSidebar.css";
import { ReactComponent as NewChatIcon } from '../assets/new-chat-icon.svg';
import { ReactComponent as SidebarToggleIcon } from '../assets/sidebar-toggle-icon.svg';
import { ReactComponent as EditIcon } from '../assets/edit-icon.svg';
import '../styles/shared.css';

const ChatSidebar = ({ user, activeSession, setActiveSession, isSidebarOpen, setIsSidebarOpen }) => {
  const [sessions, setSessions] = useState([]);
  const [newTitle, setNewTitle] = useState("");
  const [isNamingSession, setIsNamingSession] = useState(false);
  const [error, setError] = useState("");
  const [editingSessionId, setEditingSessionId] = useState(null);

  // Fetch existing sessions
  const fetchSessions = useCallback(async () => {
    try {
      const token = await user.getIdToken();
      const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSessions(response.data);
    } catch (err) {
      setError("Failed to load sessions.");
      console.error("Error fetching sessions:", err.response ? err.response.data : err.message);
    }
  }, [user]); // Add user as a dependency

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

  useEffect(() => {
    fetchSessions(); // Call the function
  }, [fetchSessions]); // Add it to the dependency array

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
            <button className="icon-button" onClick={() => {
              setSessions([{ id: 'new', title: '', isNew: true }, ...sessions]);
              setEditingSessionId('new');
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

          {/* Most Recent Section */}
          <div className="chat-sidebar-section">YOUR SESSIONS ({sessions.length})</div>
          <ul className="session-list">
            {sessions.map((session) => (
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
                          <div className="session-title">{session.title}</div>
                          <button 
                            className="edit-button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingSessionId(session.id);
                              setNewTitle(session.title);
                            }}
                          >
                            <EditIcon />
                          </button>
                        </>
                      )}
                    </div>
                    <div className="session-preview">
                      {session.preview || "No messages yet..."}
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
      </div>
    </>
  );
}  

export default ChatSidebar;