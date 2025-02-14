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
  const [loadingStates, setLoadingStates] = useState({
    archiving: new Set(),
    deleting: new Set()
  });

  // Fetch existing sessions with retry mechanism
  const fetchSessions = useCallback(async (retryCount = 0) => {
    if (!user) return;
    
    try {
      const token = await user.getIdToken();
      const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSessions(response.data);
    } catch (err) {
      console.error("Error fetching sessions:", err);
      
      // If we get a 401 and haven't exceeded retries, try again after a delay
      if (err.response?.status === 401 && retryCount < 3) {
        console.log(`Retrying fetch sessions (attempt ${retryCount + 1})...`);
        setTimeout(() => {
          fetchSessions(retryCount + 1);
        }, 1000); // Wait 1 second before retrying
      } else {
        setError("Failed to load sessions.");
      }
    }
  }, [user, setSessions]);

  // Initial fetch on mount or user change
  useEffect(() => {
    if (user) {
      // Add small initial delay to allow Firebase to fully initialize
      setTimeout(() => {
        fetchSessions();
      }, 500);
    }
  }, [fetchSessions, user]);

  // Refresh when active session changes
  useEffect(() => {
    if (activeSession) {
      fetchSessions();
    }
  }, [fetchSessions, activeSession]);

  const handleError = (message, error) => {
    setError(message);
    console.error(message, error);
  };

  const handleEdit = (id, title) => {
    setEditingSessionId(id);
    setNewTitle(title);
    setActiveSession(id);  // Set as active session when editing starts
  };

  const createNewSession = async (title = "Untitled Chat") => {
    try {
      const token = await user.getIdToken();
      
      if (activeSession) {
        try {
          await handleEndSession();
        } catch (err) {
          console.error("Error ending previous session:", err);
        }
      }

      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/sessions`,
        { title },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions([response.data, ...sessions]);
      setActiveSession(response.data.id);  // Already setting active session here
      setEditingSessionId(response.data.id);
      setNewTitle(response.data.title);
      setOpenSection('active');
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
      // Set loading state
      setLoadingStates(prev => ({
        ...prev,
        deleting: new Set([...prev.deleting, sessionId])
      }));

      const token = await user.getIdToken();
      await axios.delete(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${sessionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (sessionId === activeSession) setActiveSession(null);
    } catch (err) {
      handleError("Failed to delete session.", err);
    } finally {
      // Clear loading state
      setLoadingStates(prev => ({
        ...prev,
        deleting: new Set([...prev.deleting].filter(id => id !== sessionId))
      }));
    }
  };

  const handleArchiveSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      // Set loading state
      setLoadingStates(prev => ({
        ...prev,
        archiving: new Set([...prev.archiving, sessionId])
      }));

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
    } finally {
      // Clear loading state
      setLoadingStates(prev => ({
        ...prev,
        archiving: new Set([...prev.archiving].filter(id => id !== sessionId))
      }));
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
        onEdit={handleEdit}
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
        isArchiving={loadingStates.archiving.has(session.id)}
        isDeleting={loadingStates.deleting.has(session.id)}
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