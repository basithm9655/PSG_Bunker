// Timetable-specific JavaScript functionality

function refreshTimetable() {
    location.reload();
}

function planBunk(courseCode) {
    document.getElementById('bunkCourseName').textContent = courseCode;
    document.getElementById('timetableBunks').value = 1;
    document.getElementById('timetablePlannerResult').innerHTML = '';
    showModal('timetableBunkModal');
}

async function calculateTimetableBunk() {
    const courseCode = document.getElementById('bunkCourseName').textContent;
    const plannedBunks = parseInt(document.getElementById('timetableBunks').value);
    
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
            displayTimetableBunkResult(data);
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        showNotification('Error calculating bunk impact', 'error');
    }
}

function displayTimetableBunkResult(data) {
    const resultDiv = document.getElementById('timetablePlannerResult');
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

// Initialize timetable interactions
document.addEventListener('DOMContentLoaded', function() {
    // Add hover effects to class cards
    const classCards = document.querySelectorAll('.class-card');
    classCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // Add click to select functionality
    const classSlots = document.querySelectorAll('.class-slot');
    classSlots.forEach(slot => {
        slot.addEventListener('click', function() {
            const classCard = this.querySelector('.class-card');
            if (classCard) {
                const courseCode = classCard.dataset.course;
                planBunk(courseCode);
            }
        });
    });
    
    // Make timetable responsive
    function adjustTimetableLayout() {
        const timetableGrid = document.querySelector('.timetable-grid');
        if (!timetableGrid) return;
        
        if (window.innerWidth < 1024) {
            // Show only first 6 periods on smaller screens
            const periods = timetableGrid.querySelectorAll('.time-slot, .class-slot');
            periods.forEach((period, index) => {
                if (index >= 42) { // Hide periods beyond 6
                    period.style.display = 'none';
                }
            });
        } else {
            // Show all periods
            const periods = timetableGrid.querySelectorAll('.time-slot, .class-slot');
            periods.forEach(period => {
                period.style.display = '';
            });
        }
    }
    
    // Adjust on load and resize
    adjustTimetableLayout();
    window.addEventListener('resize', debounce(adjustTimetableLayout, 250));
});

// Debounce function from main.js
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
