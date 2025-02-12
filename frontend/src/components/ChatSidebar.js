import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./ChatSidebar.css";



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

  useEffect(() => {
    fetchSessions(); // Call the function
  }, [fetchSessions]); // Add it to the dependency array
  
  return (
    <>
      {/* Sidebar - Fully disappears when closed */}
        <div className="chat-sidebar">

          <div className="chat-sidebar-header">

          <div className="header-title">
            <span>Chats</span>
          </div>
          
          <div className = "header-button-section">
            <div className="sidebar-button">
              {isSidebarOpen && (
                <button className="toggle-sidebar" onClick={() => setIsSidebarOpen(false)}>
                  Hide Sidebar
                </button>
              )}
            </div>

            <div className="new-session-button">
              <button className="new-session-button" onClick={() => setIsNamingSession(true)}>
                + New Session
              </button>

              {/* Input for creating a new session */}
              {isNamingSession && (
                <div className="new-session-input">
                  <div className="new-session-title-input">
                    <input
                      type="text"
                      placeholder="Enter session title"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                    />
                  </div>
                  <div className="new-session-sub-buttons">
                    <button className="create-button" onClick={handleCreateSession}>Create</button>
                    <button className="cancel-button" onClick={() => setIsNamingSession(false)}>Cancel</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

          {error && <p className="error">{error}</p>}

          {/* Most Recent Section */}
          <div className="chat-sidebar-section">YOUR SESSIONS ({sessions.length})</div>
          <ul className="session-list">
            {sessions.map((session) => (
              <li
                key={session.id}
                className={`session-item ${session.id === activeSession ? "active" : ""}`}
                onClick={() => setActiveSession(session.id)}
              >
                {editingSessionId === session.id ? (
                  <button onClick={() => setEditingSessionId(null)}>Cancel</button>
                ) : (
                  <>
                    <div className="session-title">{session.title}</div>
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