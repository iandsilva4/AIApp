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
    deleting: new Set(),
    creating: false
  });

  // NEW: Store available assistants list and the currently selected assistant
  const [assistants, setAssistants] = useState([]);
  const [selectedAssistant, setSelectedAssistant] = useState(1);

  // NEW: State for new session modal
  const [showAssistantSelection, setShowAssistantSelection] = useState(false);
  const [modalSessionTitle, setModalSessionTitle] = useState("");

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

  // NEW: Fetch available assistants from the backend
  useEffect(() => {
    const fetchAssistants = async () => {
      try {
        const token = await user.getIdToken();
        const response = await axios.get(
          `${process.env.REACT_APP_BACKEND_URL}/assistants`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setAssistants(response.data);
        if (response.data && response.data.length > 0) {
          setSelectedAssistant(response.data[0].id);
        }
      } catch (err) {
        console.error("Failed to fetch assistants", err);
      }
    };
    if (user) {
      fetchAssistants();
    }
  }, [user]);

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

  const createNewSession = async (title = "New Chat") => {
    try {
      setLoadingStates(prev => ({ ...prev, creating: true }));
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
        { 
          title: modalSessionTitle || title,
          assistant_id: parseInt(selectedAssistant)
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSessions([response.data, ...sessions]);
      setActiveSession(response.data.id);
      setEditingSessionId(response.data.id);
      setNewTitle(response.data.title);
      setOpenSection('active');
      setShowAssistantSelection(false);
      setModalSessionTitle("");
    } catch (err) {
      handleError("Failed to create a new session.", err);
    } finally {
      setLoadingStates(prev => ({ ...prev, creating: false }));
    }
  };

  const handleUpdateSession = async (id, title) => {
    try {
      const token = await user.getIdToken();
      const response = await axios.put(
        `${process.env.REACT_APP_BACKEND_URL}/sessions/${id}`,
        { title, user_email: user.email },
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
          <button 
            className="icon-button" 
            title="Hide sidebar" 
            onClick={() => setIsSidebarOpen(false)}
          >
            <SidebarToggleIcon />
          </button>
          <button 
            className="icon-button" 
            onClick={() => setShowAssistantSelection(true)}
            title="New chat"
            disabled={loadingStates.creating}
          >
            {loadingStates.creating ? (
              <div className="button-spinner"></div>
            ) : (
              <NewChatIcon />
            )}
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

      {/* NEW: Modal for assistant selection & new session title */}
      {showAssistantSelection && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Create New Chat</h3>
            <div>
              <label htmlFor="modal-session-title">Chat Title:</label>
              <input 
                id="modal-session-title"
                type="text" 
                value={modalSessionTitle} 
                onChange={(e) => setModalSessionTitle(e.target.value)} 
                placeholder="New Chat"
              />
            </div>
            <div>
              <label htmlFor="assistant-select-modal">Assistant:</label>
              <select 
                id="assistant-select-modal"
                value={selectedAssistant}
                onChange={(e) => setSelectedAssistant(e.target.value)}
              >
                {assistants.map(assistant => (
                  <option key={assistant.id} value={assistant.id}>
                    {assistant.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="modal-buttons">
              <button onClick={() => createNewSession()}>Create Chat</button>
              <button onClick={() => {
                setShowAssistantSelection(false);
                setModalSessionTitle("");
              }}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatSidebar;