document.addEventListener('DOMContentLoaded', function() {
    // Load the sidebar
    fetch('sidebar.html')
        .then(response => response.text())
        .then(data => {
            document.getElementById('sidebar-container').innerHTML = data;

            // Toggle sidebar visibility
            document.querySelector('.toggle-sidebar').addEventListener('click', function() {
                document.querySelector('.sidebar').classList.toggle('active');
                document.querySelector('main').classList.toggle('full-width');
            });
        });
});