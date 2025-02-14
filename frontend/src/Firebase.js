import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup, signInWithRedirect, getRedirectResult, signOut, setPersistence, browserLocalPersistence } from "firebase/auth";

// Your Firebase configuration
const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  measurementId: process.env.REACT_APP_FIREBASE_MEASUREMENT_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Set persistence to LOCAL
setPersistence(auth, browserLocalPersistence)
  .catch((error) => {
    console.error("Error setting persistence:", error);
  });

// Get the current URL for redirect
const getRedirectUrl = () => {
  // Use environment variable if set, otherwise use current origin
  return process.env.REACT_APP_AUTH_REDIRECT_URL || window.location.origin;
};

// Configure Google provider with dynamic redirect URI
const getProvider = () => {
  const provider = new GoogleAuthProvider();
  const redirectUrl = getRedirectUrl();
  provider.setCustomParameters({
    prompt: 'select_account',
    redirect_uri: redirectUrl
  });
  return provider;
};

// Authentication functions
export const signInWithGoogle = async (isMobile = false) => {
  const provider = getProvider();
  
  if (isMobile) {
    await getRedirectResult(auth);
    await signInWithRedirect(auth, provider);
    return null;
  }
  
  const result = await signInWithPopup(auth, provider);
  return result.user;
};

export const getGoogleRedirectResult = async () => {
  const result = await getRedirectResult(auth);
  if (result) {
    return result.user;
  }
  return auth.currentUser;
};

export const logout = async () => {
  await signOut(auth);
  localStorage.removeItem('user');
  localStorage.removeItem('authToken');
};

// Add this function to help manage tokens
export const getAuthToken = async () => {
  try {
    // First try to get current user
    const currentUser = auth.currentUser;
    if (currentUser) {
      // Force token refresh
      const token = await currentUser.getIdToken(true);
      localStorage.setItem('authToken', token);
      return token;
    }
    
    // Fallback to stored token
    return localStorage.getItem('authToken');
  } catch (error) {
    console.error('Error getting auth token:', error);
    return null;
  }
};
