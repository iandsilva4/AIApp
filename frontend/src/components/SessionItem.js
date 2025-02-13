import React from 'react';
import { ReactComponent as EditIcon } from '../assets/edit-icon.svg';
import { ReactComponent as DeleteIcon } from '../assets/delete-icon.svg';
import { ReactComponent as ArchiveIcon } from '../assets/archive-icon.svg';
import { ReactComponent as UnarchiveIcon } from '../assets/unarchive-icon.svg';
import '../styles/shared.css';
import "./ChatSidebar.css";


const SessionItem = ({ 
  session, 
  isActive, 
  onSelect, 
  onEdit, 
  onArchive, 
  onDelete,
  editingId,
  newTitle,
  onTitleChange,
  onSaveTitle,
  onCancelEdit 
}) => {
  const getTimeDisplay = (timestamp) => {
    if (!timestamp) return "No messages yet...";
    const date = new Date(timestamp + 'Z');
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: new Date().getFullYear() !== date.getFullYear() ? 'numeric' : undefined,
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    }).format(date);
  };

  return (
    <li className={`session-item ${isActive ? "active" : ""} ${session.is_archived ? "archived" : ""}`}
        onClick={() => onSelect(session.id)}>
      <div className="session-header">
        {editingId === session.id ? (
          <div className="edit-input-container">
            <input
              type="text"
              className="session-edit-input"
              value={newTitle}
              onChange={(e) => onTitleChange(e.target.value)}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter' && newTitle.trim()) onSaveTitle(session.id, newTitle);
                if (e.key === 'Escape') onCancelEdit();
              }}
              onClick={(e) => e.stopPropagation()}
            />
            <div className="edit-actions">
              <button className="save-button" onClick={(e) => {
                e.stopPropagation();
                if (newTitle.trim()) onSaveTitle(session.id, newTitle);
              }}>✓</button>
              <button className="cancel-button" onClick={(e) => {
                e.stopPropagation();
                onCancelEdit();
              }}>✕</button>
            </div>
          </div>
        ) : (
          <>
            <div className={`session-title ${session.is_ended ? 'ended' : ''}`}>
              {session.title}
              {session.is_ended && <span className="ended-badge">Ended</span>}
            </div>
            <div className="session-actions">
              <button className="edit-button" onClick={(e) => {
                e.stopPropagation();
                onEdit(session.id, session.title);
              }} title="Edit chat name">
                <EditIcon />
              </button>
              <button className={`${session.is_archived ? 'unarchive' : 'archive'}-button`}
                      onClick={(e) => onArchive(e, session.id)}
                      title={`${session.is_archived ? 'Unarchive' : 'Archive'} chat`}>
                {session.is_archived ? <UnarchiveIcon /> : <ArchiveIcon />}
              </button>
              <button className="delete-button"
                      onClick={(e) => onDelete(e, session.id)}
                      title="Delete chat">
                <DeleteIcon />
              </button>
            </div>
          </>
        )}
      </div>
      <div className="session-preview">
        {session.messages?.length > 0 ? (
          <>
            <span className="preview-text">{session.preview || "Empty conversation"}</span>
            <span className="timestamp">{getTimeDisplay(session.timestamp)}</span>
          </>
        ) : (
          <span className="timestamp">No messages yet...</span>
        )}
      </div>
    </li>
  );
};

export default SessionItem; 