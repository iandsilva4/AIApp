import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./ChatSidebar.css";



const ChatSidebar = ({ user, activeSession, setActiveSession }) => {
  const [sessions, setSessions] = useState([]);
  const [newTitle, setNewTitle] = useState("");
  const [isNamingSession, setIsNamingSession] = useState(false);
  const [error, setError] = useState("");
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editedTitle, setEditedTitle] = useState("");

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

  // Edit session title
  const handleEditSessionTitle = async (sessionId) => {
    if (!editedTitle.trim()) {
      setError("Title cannot be empty.");
      return;
    }

    try {
      const token = await user.getIdToken();
      await axios.put(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${sessionId}`,
        { title: editedTitle },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions((prevSessions) =>
        prevSessions.map((session) =>
          session.id === sessionId ? { ...session, title: editedTitle } : session
        )
      );
      setEditingSessionId(null);
    } catch (err) {
      setError("Failed to update session title.");
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSessions(); // Call the function
  }, [fetchSessions]); // Add it to the dependency array
  
  return (
    <div className="chat-sidebar">
      {/* Header with title and optional icons */}
      <div className="chat-sidebar-header">
        <span>Chats</span>
      </div>
  
      {/* Input for creating a new session */}
      {isNamingSession ? (
        <div className="new-session-input">
          <input
            type="text"
            placeholder="Enter session title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
          <button onClick={handleCreateSession}>Create</button>
          <button onClick={() => setIsNamingSession(false)}>Cancel</button>
        </div>
      ) : (
        <button className="new-session-button" onClick={() => setIsNamingSession(true)}>
          + New Session
        </button>
      )}
  
      {error && <p className="error">{error}</p>}

      {/* Most Recent Section */}
      <div className="chat-sidebar-section">MOST RECENT ({sessions.length})</div>
      <ul className="session-list">
        {sessions.map((session) => (
          <li
            key={session.id}
            className={`session-item ${session.id === activeSession ? "active" : ""}`}
            onClick={() => setActiveSession(session.id)}
          >
            {editingSessionId === session.id ? (
              <>
                <input
                  type="text"
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                />
                <button onClick={() => handleEditSessionTitle(session.id)}>Save</button>
                <button onClick={() => setEditingSessionId(null)}>Cancel</button>
              </>
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
  );
};

export default ChatSidebar;