import React from 'react';
import './Streaks.css';

const Streaks = ({ streaks }) => {
  return (
    <section className="streak-section">
      <div className="streak-cards">
        <div className="streak-card">
          <span className="streak-number">{streaks.daily}</span>
          <span className="streak-label">Day Streak</span>
        </div>
        <div className="streak-card">
          <span className="streak-number">{streaks.weekly}</span>
          <span className="streak-label">Week Streak</span>
        </div>
        <div className="streak-card">
          <span className="streak-number">{streaks.monthly}</span>
          <span className="streak-label">Month Streak</span>
        </div>
      </div>
    </section>
  );
};

export default Streaks; 