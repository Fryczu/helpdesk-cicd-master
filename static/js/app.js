document.addEventListener("DOMContentLoaded", function () {
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.classList.remove("show");
      alert.classList.add("fade");
      alert.remove();
    }, 5000);
  });
});
