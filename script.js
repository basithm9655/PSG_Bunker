// Attendance management
let attendanceData = {};

function markAttendance(subjectCode, action) {
    if (!subjectCode) return;
    
    fetch('/update_attendance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            subject_code: subjectCode,
            action: action
        })
    })
    .then(response => response.json())
    .then(data => {
        attendanceData = data;
        updateAttendanceDisplay();
        showNotification(`${action === 'attend' ? 'Attended' : 'Bunked'} class successfully!`, 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error updating attendance', 'error');
    });
}

function updateAttendanceDisplay() {
    const summaryContainer = document.getElementById('attendanceSummary');
    
    if (!summaryContainer) return;
    
    if (Object.keys(attendanceData).length === 0) {
        summaryContainer.innerHTML = `
            <div class="no-data">
                <i class="fas fa-chart-bar"></i>
                <p>No attendance data yet. Start marking classes!</p>
            </div>
        `;
        return;
    }
    
    summaryContainer.innerHTML = Object.keys(attendanceData).map(subjectCode => {
        const data = attendanceData[subjectCode];
        const percentage = data.percentage;
        
        let statusClass = 'good';
        if (percentage < 75) statusClass = 'danger';
        else if (percentage < 85) statusClass = 'warning';
        
        return `
            <div class="attendance-card ${statusClass}">
                <h4>${data.subject}</h4>
                <div class="attendance-stats">
                    <div>
                        <small>Attended: ${data.attended}/${data.total_classes}</small>
                    </div>
                    <div class="percentage ${statusClass}">${percentage}%</div>
                </div>
            </div>
        `;
    }).join('');
}

function getBunkerSuggestions() {
    const threshold = document.getElementById('threshold').value;
    
    fetch('/get_bunker_suggestions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            threshold: threshold
        })
    })
    .then(response => response.json())
    .then(suggestions => {
        displaySuggestions(suggestions);
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error getting suggestions', 'error');
    });
}

function displaySuggestions(suggestions) {
    const suggestionsContainer = document.getElementById('suggestions');
    
    if (!suggestionsContainer) return;
    
    if (Object.keys(suggestions).length === 0) {
        suggestionsContainer.innerHTML = `
            <div class="no-data">
                <i class="fas fa-lightbulb"></i>
                <p>No suggestions available. Mark some classes first!</p>
            </div>
        `;
        return;
    }
    
    suggestionsContainer.innerHTML = Object.keys(suggestions).map(subjectCode => {
        const suggestion = suggestions[subjectCode];
        let cardClass = 'warning';
        let icon = 'fas fa-exclamation-triangle';
        
        if (suggestion.can_bunk > 0) {
            cardClass = 'good';
            icon = 'fas fa-check-circle';
        }
        
        return `
            <div class="suggestion-card ${cardClass}">
                <h4>${suggestion.subject}</h4>
                <p><strong>Current:</strong> ${suggestion.current_percentage}%</p>
                <p><strong>Suggestion:</strong> ${suggestion.message}</p>
                <div style="margin-top: 0.5rem;">
                    <i class="${icon}"></i>
                </div>
            </div>
        `;
    }).join('');
}

function resetAttendance() {
    if (!confirm('Are you sure you want to reset all attendance data?')) {
        return;
    }
    
    fetch('/reset_attendance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        attendanceData = data;
        updateAttendanceDisplay();
        showNotification('Attendance data reset successfully!', 'success');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error resetting attendance', 'error');
    });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}"></i>
        <span>${message}</span>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#06b6d4'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize attendance display
    updateAttendanceDisplay();
    
    // Add event listeners for buttons
    const suggestionsBtn = document.getElementById('getSuggestions');
    const resetBtn = document.getElementById('resetAttendance');
    
    if (suggestionsBtn) {
        suggestionsBtn.addEventListener('click', getBunkerSuggestions);
    }
    
    if (resetBtn) {
        resetBtn.addEventListener('click', resetAttendance);
    }
    
    // Add threshold input validation
    const thresholdInput = document.getElementById('threshold');
    if (thresholdInput) {
        thresholdInput.addEventListener('change', function() {
            let value = parseInt(this.value);
            if (value < 0) this.value = 0;
            if (value > 100) this.value = 100;
        });
    }
});