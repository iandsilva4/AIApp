import React, { useEffect } from "react";
import { signInWithGoogle, auth } from "../Firebase";
import { onAuthStateChanged } from "firebase/auth";
import "./Login.css";
import { 
  FaGoogle, 
  FaRobot, 
  FaBrain, 
  FaUserCheck, 
  FaChartLine 
} from "react-icons/fa";

const Login = ({ setUser }) => {
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        setUser(user);
        localStorage.setItem("user", JSON.stringify(user));
      } else {
        setUser(null);
        localStorage.removeItem("user");
      }
    });

    return () => unsubscribe();
  }, [setUser]);

  const handleLogin = async () => {
    const loggedInUser = await signInWithGoogle();
    if (loggedInUser) {
      setUser(loggedInUser);
    }
  };

  return (
    <div className="landing-page">
      <div className="grid-background"></div>
      <div className="grid-overlay"></div>
      <div className="grid-distortion"></div>
      
      <div className="floating-elements">
        <div className="floating-element element-1"></div>
        <div className="floating-element element-2"></div>
        <div className="floating-element element-3"></div>
        
        {/* Horizontal lines */}

        
        {/* Diagonal lines */}
        <div className="moving-line line-5"></div>
        <div className="moving-line line-6"></div>
      </div>
      
      <div className="gradient-spots">
        <div className="gradient-spot spot-1"></div>
        <div className="gradient-spot spot-2"></div>
        <div className="gradient-spot spot-3"></div>
      </div>
      
      <div className="landing-content">
        {/* Hero Section */}
        <div className="hero-section">
          <h1>Your AI Life Coach for Deep, Personalized Conversations</h1>
          <p className="hero-subtitle">
            An AI that truly knows you—helping you reflect, grow, and gain clarity through meaningful sessions.
          </p>
          <button className="google-login-button" onClick={handleLogin}>
            <FaGoogle className="google-icon" /> Start Your Journey
          </button>
        </div>
  
        {/* Features Section */}
        <div className="features-section">
          <div className="feature-card">
            <FaBrain className="feature-icon" />
            <h3>AI-Powered Sessions</h3>
            <p>Conversations that adapt to you—helping you process thoughts, emotions, and decisions in a way that feels natural.</p>
          </div>
  
          <div className="feature-card">
            <FaUserCheck className="feature-icon" />
            <h3>Choose Your AI Persona</h3>
            <p>Select from different AI personalities—whether you prefer an empathetic guide, a direct coach, or a reflective thinker.</p>
          </div>
  
          <div className="feature-card">
            <FaChartLine className="feature-icon" />
            <h3>Track Your Growth</h3>
            <p>Personalized insights help you see patterns, track progress, and understand yourself over time.</p>
          </div>

        </div>
      </div>
    </div>
  );
  
};

export default Login;


/*
return (
    <div className="login-page">
      {user ? (
        <div className="login-card">
          <p className="welcome-text">Welcome, {user.displayName}</p>
          <button className="logout-button" onClick={handleLogout}>Logout</button>
        </div>
      ) : (
        <div className="login-card">
          <h2>Log in</h2>
          <button className="google-login-button" onClick={handleLogin}>
            <FaGoogle className="google-icon" /> Continue with Google
          </button>

          <div className="divider"><span>or</span></div>

          <div className="input-container">
            <input type="email" placeholder="Email" className="input-field" />
          </div>

          <div className="input-container">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              className="input-field"
            />
            <span
              className="password-toggle"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <FaRegEyeSlash /> : <FaRegEye />}
            </span>
          </div>

          <div className="forgot-password">
            <a href="#">Forgot Password?</a>
          </div>

          <button className="login-button">Log in</button>

          <p className="signup-text">
            New user? <a href="#">Sign up</a>
          </p>
        </div>
      )}
    </div>
  );
};
*/