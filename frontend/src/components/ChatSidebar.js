import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import "./ChatSidebar.css";
import { ReactComponent as NewChatIcon } from '../assets/new-chat-icon.svg';
import { ReactComponent as SidebarToggleIcon } from '../assets/sidebar-toggle-icon.svg';
import '../styles/shared.css';
import SessionItem from './SessionItem';

const ChatSidebar = ({ user, activeSession, setActiveSession, setIsSidebarOpen, sessions, setSessions, handleEndSession }) => {
  const [newTitle, setNewTitle] = useState("");
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

  const handleError = (message, error) => {
    setError(message);
    console.error(message, error);
  };

  const createNewSession = async (title = "Untitled Chat") => {
    try {
      const token = await user.getIdToken();
      
      if (activeSession) {
        try {
          await handleEndSession();
        } catch (err) {
          // If ending the session fails, log it but continue with creating new session
          console.error("Error ending previous session:", err);
        }
      }

      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/sessions`,
        { title },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions([response.data, ...sessions]);
      setActiveSession(response.data.id);
      setNewTitle("");
    } catch (err) {
      handleError("Failed to create a new session.", err);
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

      setSessions(prev => prev.map(s => s.id === id ? response.data : s));
      setEditingSessionId(null);
      setNewTitle("");
    } catch (err) {
      handleError("Failed to update the session.", err);
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this chat?")) return;

    try {
      const token = await user.getIdToken();
      await axios.delete(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${sessionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (sessionId === activeSession) setActiveSession(null);
    } catch (err) {
      handleError("Failed to delete session.", err);
    }
  };

  const handleArchiveSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      const token = await user.getIdToken();
      const response = await axios.put(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${sessionId}/archive`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions(prev => prev.map(s => s.id === sessionId ? response.data : s));
      if (sessionId === activeSession) setActiveSession(null);
    } catch (err) {
      handleError("Failed to archive session.", err);
    }
  };

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(""), 3000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const renderSessionList = (isArchived) => {
    const filteredSessions = sessions.filter(s => s.is_archived === isArchived);
    return filteredSessions.map(session => (
      <SessionItem
        key={session.id}
        session={session}
        isActive={session.id === activeSession}
        onSelect={setActiveSession}
        onEdit={(id, title) => {
          setEditingSessionId(id);
          setNewTitle(title);
        }}
        onArchive={handleArchiveSession}
        onDelete={handleDeleteSession}
        editingId={editingSessionId}
        newTitle={newTitle}
        onTitleChange={setNewTitle}
        onSaveTitle={handleUpdateSession}
        onCancelEdit={() => {
          setEditingSessionId(null);
          setNewTitle('');
        }}
      />
    ));
  };

  return (
    <div className="chat-sidebar">
      <div className="chat-sidebar-header">
        <div className="header-title">Chats</div>
        <div className="header-button-section">
          <button className="icon-button" onClick={() => setIsSidebarOpen(false)}>
            <SidebarToggleIcon />
          </button>
          <button className="icon-button" onClick={() => createNewSession()} title="New chat">
            <NewChatIcon />
          </button>
        </div>
      </div>

      {error && <div className="error-message fade-out">{error}</div>}

      <div className="lists-container">
        <div className="active-sessions">
          <div className="chat-sidebar-section" onClick={() => setOpenSection(s => s === 'active' ? null : 'active')}>
            <span>YOUR SESSIONS ({sessions.filter(s => !s.is_archived).length})</span>
            <span className={`section-toggle ${openSection === 'active' ? 'open' : ''}`}>▼</span>
          </div>
          <ul className={`session-list ${openSection !== 'active' ? 'collapsed' : ''}`}>
            {renderSessionList(false)}
          </ul>
        </div>

        {sessions.some(s => s.is_archived) && (
          <div className="archived-sessions">
            <div className="chat-sidebar-section" onClick={() => setOpenSection(s => s === 'archived' ? null : 'archived')}>
              <span>ARCHIVED ({sessions.filter(s => s.is_archived).length})</span>
              <span className={`section-toggle ${openSection === 'archived' ? 'open' : ''}`}>▼</span>
            </div>
            <ul className={`session-list ${openSection !== 'archived' ? 'collapsed' : ''}`}>
              {renderSessionList(true)}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatSidebar;