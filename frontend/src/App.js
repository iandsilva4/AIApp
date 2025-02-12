import React, { useState, useEffect } from "react";
import ChatSidebar from "./components/ChatSidebar";
import ChatWindow from "./components/ChatWindow";
import Login from "./components/Login";
import Logout from "./components/Logout";
import { auth } from "./Firebase";
import { onAuthStateChanged } from "firebase/auth";
import "./App.css";


const App = () => {

  const [user, setUser] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // Sidebar starts open
  const [isAuthReady, setIsAuthReady] = useState(false); // Add this state
  const [sessions, setSessions] = useState([]);


  // Listen for authentication state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setIsAuthReady(true); // Set this to true when auth state is determined
    });

    return () => unsubscribe();
  }, []);

  // Show loading while auth is initializing
  if (!isAuthReady) {
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

  // Add this function to handle session updates
  const handleSessionUpdate = (updatedSession) => {
    setSessions(prevSessions => 
      prevSessions.map(session => 
        session.id === updatedSession.id ? updatedSession : session
      )
    );
  };

  return (
    <div className="app-container">
      <header className="header">
        <p>Welcome, {user.displayName} ({user.email})</p>
        <Logout user={user} setUser={setUser} />
      </header>

      {/* Apply 'sidebar-hidden' class when sidebar is closed */}
      <div className={"app-content"}>
        {isSidebarOpen ? (
          <div className="sidebar-container">
            <ChatSidebar
              user={user}
              activeSession={activeSession}
              setActiveSession={setActiveSession}
              setIsSidebarOpen={setIsSidebarOpen}
              sessions={sessions}
              setSessions={setSessions}
            />
          </div>
        ) : null}

        <div className="chat-window-container">
          <ChatWindow 
            user={user} 
            activeSession={activeSession} 
            isSidebarOpen={isSidebarOpen}
            setIsSidebarOpen={setIsSidebarOpen}
            sessions={sessions}
            setSessions={setSessions}
          />
        </div>
      </div>
    </div>
  );
};

export default App;