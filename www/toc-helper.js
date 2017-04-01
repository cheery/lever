(function(){
    var last_y = 0;
    function toc_action(y) {
        if (y > 800) {
            if (y - last_y < 0) {
                document.getElementById("toc-link").className = "visible";
            } else if (y - last_y > 0) {
                document.getElementById("toc-link").className = "";
            }
        } else
        if (last_y > 800) {
            document.getElementById("toc-link").className = "";
        }

        last_y = y;
    }

    var scroll_y = 0;
    var ticking = false;
    window.addEventListener('scroll', function(e) {
      scroll_y = window.scrollY;
      if (!ticking) {
        window.requestAnimationFrame(function() {
          toc_action(scroll_y);
          ticking = false;
        });
      }
      ticking = true;
    });
})();
