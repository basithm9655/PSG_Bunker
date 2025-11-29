// Attendance-specific JavaScript functionality

// Bunk Planner functionality
function showBunkPlanner() {
    showModal('bunkPlannerModal');
}

function showManualEntry() {
    showModal('manualEntryModal');
}

async function calculateBunkImpact() {
    const courseCode = document.getElementById('plannerCourse').value;
    const plannedBunks = parseInt(document.getElementById('plannedBunks').value);
    
    if (isNaN(plannedBunks) || plannedBunks < 0) {
        showNotification('Please enter a valid number of classes', 'error');
        return;
    }
    
    try {
        const response = await fetch('/bunk_planner', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                course_code: courseCode,
                planned_bunks: plannedBunks
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayBunkPlannerResult(data);
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        showNotification('Error calculating bunk impact', 'error');
    }
}

function displayBunkPlannerResult(data) {
    const resultDiv = document.getElementById('plannerResult');
    const statusClass = data.status;
    const canBunk = data.can_bunk;
    
    resultDiv.innerHTML = `
        <h4><i class="fas fa-chart-line"></i> Bunk Impact Analysis</h4>
        <div class="planner-stats">
            <div class="planner-stat">
                <div class="value">${data.current_percentage}%</div>
                <div class="label">Current</div>
            </div>
            <div class="planner-stat">
                <div class="value ${statusClass}">${data.new_percentage}%</div>
                <div class="label">After Bunking</div>
            </div>
        </div>
        <div class="planner-recommendation ${statusClass}">
            <i class="fas fa-${canBunk ? 'check-circle' : 'exclamation-triangle'}"></i>
            ${canBunk ? 
                'You can safely bunk these classes!' : 
                'Warning: Bunking may drop your attendance below threshold!'}
        </div>
    `;
}

async function saveManualEntry() {
    const courseCode = document.getElementById('manualCourse').value;
    const additionalHours = parseInt(document.getElementById('additionalHours').value);
    const additionalPresent = parseInt(document.getElementById('additionalPresent').value);
    
    if (isNaN(additionalHours) || isNaN(additionalPresent) || additionalHours < 0 || additionalPresent < 0) {
        showNotification('Please enter valid numbers', 'error');
        return;
    }
    
    if (additionalPresent > additionalHours) {
        showNotification('Present hours cannot exceed total hours', 'error');
        return;
    }
    
    try {
        const response = await fetch('/update_manual_attendance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                course_code: courseCode,
                additional_hours: additionalHours,
                additional_present: additionalPresent
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Manual attendance updated successfully', 'success');
            closeModal('manualEntryModal');
            // Refresh the page to show updated data
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        showNotification('Error saving manual entry', 'error');
    }
}

async function clearManualData() {
    if (!confirm('Are you sure you want to clear all manual attendance data?')) {
        return;
    }
    
    try {
        const response = await fetch('/clear_manual_attendance', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Manual data cleared successfully', 'success');
            // Refresh the page
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        showNotification('Error clearing manual data', 'error');
    }
}

// Initialize attendance page
document.addEventListener('DOMContentLoaded', function() {
    // Add any attendance-specific initialization here
    
    // Add click handlers for percentage bars to show more details
    const percentageBars = document.querySelectorAll('.percentage-bar');
    percentageBars.forEach(bar => {
        bar.addEventListener('click', function() {
            const percentage = this.querySelector('.percentage-text').textContent;
            const row = this.closest('tr');
            const courseCode = row.querySelector('td:first-child strong').textContent;
            
            showNotification(`Detailed view for ${courseCode}: ${percentage} attendance`, 'info');
        });
    });
});
