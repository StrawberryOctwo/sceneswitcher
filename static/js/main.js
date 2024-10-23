const open_menu_button = document.querySelector(".menu"),
    menu_wrapper = document.querySelector(".menu_wrapper"),
    close_menu_button = document.querySelector(".close_menu");

open_menu_button.addEventListener("click", () => {
    menu_wrapper.style.display = "flex"
})

close_menu_button.addEventListener("click", () => {
    menu_wrapper.style.display = "none"
})

document.addEventListener('DOMContentLoaded', () => {
    const colorInput = document.getElementById('fontColor');
    const colorValue = document.querySelector('.color-value');
    const textContent = document.getElementById('textContent');
    const subtitleText = document.getElementById('subtitleText');

    // Function to update the color
    function updateColor() {
        const selectedColor = colorInput.value;
        colorValue.textContent = selectedColor; // Update the color value display
        textContent.style.color = selectedColor; // Update the text color
        subtitleText.style.color = selectedColor; // Update the subtitle color
    }

    // Event listener for color input change
    colorInput.addEventListener('input', updateColor);

    // Initialize with default color
    updateColor();
});




 function redirectToLogin() {
     window.location.href = '/login'; // Redirects to the /login route
 }

function redirectToApp() {
    window.location.href = '/app'; // Redirect to the /app route
}

// Bind event listeners once DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Attach event listener to all buttons with the class "get_started"
    document.querySelector('.login').addEventListener('click', redirectToLogin);
    const getStartedButtons = document.querySelectorAll('.get_started');
    
    getStartedButtons.forEach(button => {
        // button.addEventListener('click', redirectToApp);
    });
});