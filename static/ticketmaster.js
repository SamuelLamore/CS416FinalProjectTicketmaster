        document.documentElement.setAttribute("data-theme", localStorage.getItem("theme"));
        function addOrRemoveFavorite(url, num) {
            event.preventDefault();
            $.ajax({
                url: url,
                success: function (response) {
                    if (response["action"] === "added") {
                        document.getElementById(`star-fill-${num}`).hidden = false;
                        document.getElementById(`star-outline-${num}`).hidden = true;
                    } else {
                        document.getElementById(`star-fill-${num}`).hidden = true;
                        document.getElementById(`star-outline-${num}`).hidden = false;
                    }
                }
            });
        }

        function swapTheme(btn) {
            if (document.documentElement.getAttribute("data-theme") === "dark") {
                document.documentElement.setAttribute("data-theme", "light");
                localStorage.setItem("theme", "light");
                btn.innerHTML = `<i class="bi bi-moon-fill"></i>`;
            } else {
                btn.innerHTML = `<i class="bi bi-sun-fill"></i>`;
                document.documentElement.setAttribute("data-theme", "dark");
                localStorage.setItem("theme", "dark");
            }
        }