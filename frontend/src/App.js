import React, { useState, useEffect } from "react";
import ChatSidebar from "./components/ChatSidebar";
import ChatWindow from "./components/ChatWindow";
import Login from "./components/Login";
import Logout from "./components/Logout";
import { auth } from "./Firebase";
import { onAuthStateChanged } from "firebase/auth";
import "./App.css";
import Dashboard from "./components/Dashboard";
import { MdDashboard } from "react-icons/md";
import { IoChatboxEllipses } from "react-icons/io5";


const App = () => {

  const [user, setUser] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // Sidebar starts open
  const [isAuthReady, setIsAuthReady] = useState(false); // Add this state
  const [sessions, setSessions] = useState([]);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [isCreatingNewSession, setIsCreatingNewSession] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [isTokenReady, setIsTokenReady] = useState(false);


  // Listen for authentication state changes
  useEffect(() => {
    // Try to get user from localStorage first
    const savedUser = localStorage.getItem("user");
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem("user");
        localStorage.removeItem('authToken');
      }
    }

    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      if (currentUser) {
        try {
          // Get fresh token
          const token = await currentUser.getIdToken();
          localStorage.setItem('authToken', token);
          setUser(currentUser);
          localStorage.setItem("user", JSON.stringify(currentUser));
          setIsTokenReady(true);
        } catch (e) {
          console.error("Error getting token:", e);
          setIsTokenReady(false);
        }
      } else {
        setUser(null);
        localStorage.removeItem("user");
        localStorage.removeItem('authToken');
        setActiveSession(null);
        setSessions([]);
        setIsTokenReady(false);
      }
      setIsAuthReady(true);
    });

    return () => unsubscribe();
  }, []);

  // Add window resize listener
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Show loading while auth is initializing
  if (!isAuthReady || (user && !isTokenReady)) {
    return (
      <div className="app-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Initializing...</p>
        </div>
      </div>
    );
  }

  // Show login if not authenticated
  if (!user) {
    return <Login setUser={setUser} />;
  }

  return (
    <div className="app-container">
      <header className="header">
        <p>Welcome, {user.displayName?.split(' ')[0]} ({user.email})</p>
        <div className="header-buttons">
          <button 
            className="dashboard-button"
            onClick={() => setShowDashboard(!showDashboard)}
          >
            {showDashboard ? (
              <>
                <IoChatboxEllipses className="button-icon" />
                <span>Chat</span>
              </>
            ) : (
              <>
                <MdDashboard className="button-icon" />
                <span>Dashboard</span>
              </>
            )}
          </button>
          <Logout user={user} setUser={setUser} />
        </div>
      </header>

      {showDashboard ? (
        <div className="app-content">
          <div className="dashboard-wrapper">
            <Dashboard user={user} />
          </div>
        </div>
      ) : (
        <div className={`app-content ${isMobile && activeSession ? 'show-chat' : ''}`}>
          {/* Show sidebar if it's open on desktop, or if on mobile and no active session */}
          {(isSidebarOpen || (isMobile && !activeSession)) && (
            <div className="sidebar-container">
              <ChatSidebar
                user={user}
                activeSession={activeSession}
                setActiveSession={(sessionId) => {
                  setActiveSession(sessionId);
                  if (isMobile) {
                    setIsSidebarOpen(false);
                  }
                }}
                setIsSidebarOpen={setIsSidebarOpen}
                sessions={sessions}
                setSessions={setSessions}
                setIsCreatingNewSession={setIsCreatingNewSession}
              />
            </div>
          )}

          {/* Show chat window if not on mobile, or if on mobile and has active session */}
          {(!isMobile || (isMobile && activeSession)) && (
            <div className="chat-window-container">
              <ChatWindow 
                user={user} 
                activeSession={activeSession} 
                isSidebarOpen={isSidebarOpen}
                setIsSidebarOpen={(open) => {
                  setIsSidebarOpen(open);
                  if (isMobile && open) {
                    setActiveSession(null);
                  }
                }}
                sessions={sessions}
                setSessions={setSessions}
                setActiveSession={setActiveSession}
                isCreatingNewSession={isCreatingNewSession}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default App;