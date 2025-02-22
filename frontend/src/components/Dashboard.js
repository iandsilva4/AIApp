import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import ContributionGraph from './ContributionGraph';
import Streaks from './Streaks';
import MoodTracker from './MoodTracker';
import axios from "axios";
import { FaFire, FaChartArea, FaSmile } from 'react-icons/fa';


const Dashboard = ({ user }) => {
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [contributionData, setContributionData] = useState({});
  const [availableYears, setAvailableYears] = useState([]);
  const [streaks, setStreaks] = useState({
    daily: 0,
    weekly: 0,
    monthly: 0
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = await user.getIdToken();
        const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/sessions/stats`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        const data = response.data;
        
        setContributionData(data.contributions);
        setStreaks(data.streaks);
        
        const years = Object.keys(data.contributions);
        setAvailableYears(years.sort().reverse());
        
        if (years.length > 0) {
          setSelectedYear(Math.max(...years.map(Number)));
        }
      } catch (error) {
        console.error('Error fetching stats:', error);
      }
    };

    if (user) {
      fetchStats();
    }
  }, [user]);

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h2>Your Learning Journey</h2>
      </div>
      
      <div className="dashboard-content">
        <div className="dashboard-section">
          <div className="section-header">
            <h3>
              <FaFire style={{ color: '#f97316', marginRight: '8px' }} />
              Activity Streaks
            </h3>
          </div>
          <Streaks streaks={streaks} />
        </div>

        <div className="dashboard-section">
          <div className="section-header">
            <h3>
              <FaChartArea style={{ color: '#6366f1', marginRight: '8px' }} />
              Session Activity
            </h3>
          </div>
          <ContributionGraph 
            data={contributionData[selectedYear] || {}} 
            year={selectedYear}
            availableYears={availableYears}
            onYearChange={setSelectedYear}
          />
        </div>

        <div className="dashboard-section">
          <div className="section-header">
            <h3>
              <FaSmile style={{ color: '#10b981', marginRight: '8px' }} />
              Mood Tracker
            </h3>
          </div>
          <MoodTracker user={user}/>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 