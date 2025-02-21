import React from 'react';
import './ContributionGraph.css';

const ContributionGraph = ({ data, year, availableYears, onYearChange }) => {
  // Helper to convert UTC date to local date string
  const toLocalDate = (date) => {
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return new Date(date.toLocaleString('en-US', { timeZone: userTimezone }));
  };

  // Generate dates for specific year
  const generateDates = () => {
    const start = new Date(year, 0, 1); // January 1st
    const end = new Date(year, 11, 31); // December 31st
    
    const weeks = [];
    let currentWeek = new Array(start.getDay()).fill(null); // Fill with null until first day
    const current = new Date(start);
    
    while (current <= end) {
      currentWeek.push(new Date(current));
      
      if (current.getDay() === 6) {
        while (currentWeek.length < 7) {
          currentWeek.push(null);
        }
        weeks.push(currentWeek);
        currentWeek = [];
      }
      
      current.setDate(current.getDate() + 1);
    }
    
    // Fill the last week with null after the last day if needed
    if (currentWeek.length > 0) {
      while (currentWeek.length < 7) {
        currentWeek.push(null);
      }
      weeks.push(currentWeek);
    }
    
    return weeks;
  };

  // Helper to format date for display in user's timezone
  const formatDateForDisplay = (date) => {
    return toLocalDate(date).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
    });
  };

  // Helper to format date as YYYY-MM-DD for data lookup
  const formatDate = (date) => {
    if (!date) return '';
    const localDate = toLocalDate(date);
    return localDate.toISOString().split('T')[0];
  };

  // Get contribution level (active/inactive) for a date
  const getContributionLevel = (date) => {
    if (!date) return 'empty';
    const dateStr = formatDate(date);
    const dateData = data[dateStr];
    return dateData?.timestamps?.length > 0 ? 'active' : 'inactive';
  };

  // Generate month labels with their positions
  const getMonthLabels = () => {
    const weeks = generateDates();
    const months = [];
    let currentMonth = '';
    let weekIndex = 0;
    
    weeks.forEach(week => {
      const firstValidDate = week.find(date => date !== null);
      if (firstValidDate) {
        const month = toLocalDate(firstValidDate).toLocaleString('default', { month: 'short' });
        if (month !== currentMonth) {
          months.push({ name: month, position: weekIndex });
          currentMonth = month;
        }
      }
      weekIndex++;
    });
    
    return months;
  };

  const weeks = generateDates();
  const monthLabels = getMonthLabels();
  const weekDays = ['Sun', '', 'Tue', '', 'Thu', '', 'Sat'];

  return (
    <section className="contribution-section">
      <div className="contribution-header">
        <div className="year-selector">
          {availableYears.map((yearOption) => (
            <button
              key={yearOption}
              className={`year-button ${yearOption === year ? 'active' : ''}`}
              onClick={() => onYearChange(yearOption)}
              aria-pressed={yearOption === year}
            >
              {yearOption}
            </button>
          ))}
        </div>
      </div>

      <div className="contribution-graph-container">
        <div className="graph-labels">
          <div className="month-labels">
            {monthLabels.map((month, i) => (
              <div 
                key={i} 
                className="month-label"
                style={{ marginLeft: i === 0 ? 0 : `${month.position * 13}px` }}
              >
                {month.name}
              </div>
            ))}
          </div>
          <div className="day-labels">
            {weekDays.map((day, i) => (
              <span key={i}>{day}</span>
            ))}
          </div>
        </div>
        
        <div className="contribution-grid">
          {weeks.map((week, weekIndex) => (
            <div key={weekIndex} className="contribution-week">
              {week.map((date, dayIndex) => (
                <div
                  key={`${weekIndex}-${dayIndex}`}
                  className={`contribution-cell ${date ? getContributionLevel(date) : 'empty'}`}
                  title={date ? `${formatDateForDisplay(date)}` : ''}
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ContributionGraph; 