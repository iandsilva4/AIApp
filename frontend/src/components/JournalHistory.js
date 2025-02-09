import { auth } from "../Firebase";
import { onAuthStateChanged } from "firebase/auth";
import axios from "axios";
import { useState, useEffect } from "react";

const JournalHistory = () => {
  const [user, setUser] = useState(null);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newEntry, setNewEntry] = useState(""); // Store new journal entry input
  const [submitting, setSubmitting] = useState(false); // Submission state

  // Fetch journal entries for the logged-in user
  const fetchEntries = async (currentUser) => {
    try {
      setError(null);

      if (!currentUser) {
        setError("You must be logged in to view journal entries.");
        return;
      }

      const token = await currentUser.getIdToken();

      // Fetch user-specific journal entries
      const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/entries`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      console.log("Fetched entries:", response.data);

      setEntries(response.data);
    } catch (err) {
      console.error("Error fetching entries:", err);
      setError("Failed to load journal entries. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Listen for authentication state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser); // Update the user state
      if (currentUser) {
        fetchEntries(currentUser); // Use fetchEntries here
      } else {
        setEntries([]); // Clear entries when logged out
      }
    });

    return () => unsubscribe(); // Cleanup on unmount
  }, []);

  // Handle form submission for adding new journal entries
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    if (!user) {
      setError("You must be logged in to add a journal entry.");
      setSubmitting(false);
      return;
    }

    try {
      const token = await user.getIdToken();

      // Send journal entry to backend
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/summarize`,
        {
          entry: newEntry,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      console.log("New entry response:", response.data);

      // Add new entry to state
      setEntries([
        {
          id: Date.now(),
          text: newEntry,
          summary: response.data.summary,
          timestamp: new Date().toISOString(),
        },
        ...entries,
      ]);
      setNewEntry("");
    } catch (err) {
      console.error("Error adding journal entry:", err);
      setError("Failed to add a new journal entry. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // Logout function
  const handleLogout = async () => {
    await auth.signOut();
    setUser(null);
    setEntries([]);
  };

  return (
    <div>
      {user ? (
        <div>
          <p>Welcome, {user.displayName} ({user.email})</p>
          <button onClick={handleLogout}>Logout</button>

          {/* Form to Add New Entry */}
          <form onSubmit={handleSubmit}>
            <textarea
              value={newEntry}
              onChange={(e) => setNewEntry(e.target.value)}
              placeholder="Write your journal entry here..."
              rows="5"
              cols="50"
            ></textarea>
            <br />
            <button type="submit" disabled={submitting || !newEntry}>
              {submitting ? "Submitting..." : "Add Entry"}
            </button>
          </form>
        </div>
      ) : (
        <p>Please log in to view your journal entries.</p>
      )}

      {/* Error Messages */}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Loading Spinner */}
      {loading && <p>Loading journal history...</p>}

      {/* Display Entries */}
      {!loading && entries.length === 0 && <p>No journal entries found.</p>}
      {!loading && entries.length > 0 && (
        <ul>
          {entries.map((entry) => (
            <li key={entry.id}>
              <p><strong>Entry:</strong> {entry.text}</p>
              <p><strong>Summary:</strong> {entry.summary}</p>
              <small>{new Date(entry.timestamp).toLocaleString()}</small>
              <hr />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default JournalHistory;
