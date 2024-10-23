function redirectToLogin() {
     window.location.href = '/login'; // Redirects to the /login route
 }

// function redirectToApp() {
//     window.location.href = '/app'; // Redirect to the /app route
// }

// Bind event listeners once DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Attach event listener to all buttons with the class "get_started"

    const getStartedButtons = document.querySelectorAll('.get-started');
    
    // getStartedButtons.forEach(button => {
    //     button.addEventListener('click', redirectToApp);

	// document.getElementById("menu-button").addEventListener("click", function () {
	// document.getElementById("modal").style.width = "100%";
	// document.getElementById("modal").style.color = "#ffffff";
	// });
	
	// document.getElementById("close-button").addEventListener("click", function () {
	// document.getElementById("modal").style.width = "0";
	// document.getElementById("modal").style.overflow = "hidden";
	// document.getElementById("modal").style.color = "transparent";
	// });
    // });
});

