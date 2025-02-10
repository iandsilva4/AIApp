import React, { useState, useEffect } from "react";
import ChatSidebar from "./components/ChatSidebar";
import ChatWindow from "./components/ChatWindow";
import Login from "./components/Login";
import { auth } from "./Firebase";
import { onAuthStateChanged, signOut } from "firebase/auth";
import "./styles.css";


const App = () => {

  const [user, setUser] = useState(null);
  const [activeSession, setActiveSession] = useState(null);

  // Listen for authentication state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });

    return () => unsubscribe();
  }, []);

  const handleLogout = async () => {
    await signOut(auth);
    setUser(null);
    setActiveSession(null);
  };

  if (!user) {
    return <Login />;
  }

  return (
    <div className="app-container">
      <header className="header">
        <p>
          Welcome, {user.displayName} ({user.email})
        </p>
        <button onClick={handleLogout}>Logout</button>
      </header>

      {/* FLEX CONTAINER FOR SIDEBAR AND CHAT WINDOW */}
      <div className="app-content">
        <div className="sidebar-container">
          <ChatSidebar
            user={user}
            activeSession={activeSession}
            setActiveSession={setActiveSession}
          />
        </div>
        <div className="chat-window-container">
          <ChatWindow
            user={user}
            activeSession={activeSession}
          />
        </div>  
      </div>
    </div>
  );
};

export default App;