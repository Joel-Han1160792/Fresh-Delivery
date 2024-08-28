(function ($) {
  "use strict";

  // Spinner
  var spinner = function () {
    setTimeout(function () {
      if ($("#spinner").length > 0) {
        $("#spinner").removeClass("show");
      }
    }, 1);
  };
  spinner();

  // Initiate the wowjs
  new WOW().init();

  // Fixed Navbar
  $(window).scroll(function () {
    if ($(window).width() < 992) {
      if ($(this).scrollTop() > 45) {
        $(".fixed-top").addClass("bg-white shadow");
      } else {
        $(".fixed-top").removeClass("bg-white shadow");
      }
    } else {
      if ($(this).scrollTop() > 45) {
        $(".fixed-top").addClass("bg-white shadow").css("top", 0);
      } else {
        $(".fixed-top").removeClass("bg-white shadow").css("top", 0);
      }
    }
  });

  // Back to top button
  $(window).scroll(function () {
    if ($(this).scrollTop() > 300) {
      $(".back-to-top").fadeIn("slow");
    } else {
      $(".back-to-top").fadeOut("slow");
    }
  });
  $(".back-to-top").click(function () {
    $("html, body").animate({ scrollTop: 0 }, 300);
    return false;
  });

  //Voice search
  // The speech recognition interface lives on the browser’s window object
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition; // if none exists -> undefined

  if (SpeechRecognition) {
    console.log("Your Browser supports speech Recognition");

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    // recognition.lang = "en-US";

    $(".micBtn").click(function () {
      var $icon = $(this).find(".fa");
      if ($icon.hasClass("fa-microphone")) {
        $icon.removeClass("fa-microphone").addClass("fa-microphone-slash");
        // Start Voice Recognition
        recognition.start(); // First time you have to allow access to mic!
      } else {
        $icon.removeClass("fa-microphone-slash").addClass("fa-microphone");
        recognition.stop();
      }
    });
    $("#searchBox").focusout(function () {
      recognition.stop();
      $(".micBtn")
        .find(".fa")
        .removeClass("fa-microphone-slash")
        .addClass("fa-microphone");
    });
    recognition.addEventListener("start", startSpeechRecognition); // <=> recognition.onstart = function() {...}
    function startSpeechRecognition() {
      $("#searchBox").focus();
      console.log("Voice activated, SPEAK");
      $("#searchTip").text("Speak....");
    }

    recognition.addEventListener("end", endSpeechRecognition); // <=> recognition.onend = function() {...}
    function endSpeechRecognition() {
      $("#searchBox").focus();
      console.log("Speech recognition service disconnected");
      $("#searchTip").text("");
    }

    recognition.addEventListener("result", resultOfSpeechRecognition); // <=> recognition.onresult = function(event) {...} - Fires when you stop talking
    function resultOfSpeechRecognition(event) {
      const current = event.resultIndex;
      const transcript = event.results[current][0].transcript;

      if (transcript.toLowerCase().trim() === "stop recording") {
        recognition.stop();
      } else if (!$("#searchBox").val()) {
        $("#searchBox").val(transcript);
      } else {
        if (transcript.toLowerCase().trim() === "go") {
          searchForm.submit();
        } else if (transcript.toLowerCase().trim() === "reset input") {
          $("#searchBox").val("");
        } else {
          $("#searchBox").val(transcript);
        }
      }
      // searchFormInput.value = transcript;
      // searchFormInput.focus();
      // setTimeout(() => {
      //   searchForm.submit();
      // }, 500);
    }
  } else {
    console.log("Your Browser does not support speech Recognition");
    //info.textContent = "Your Browser does not support Speech Recognition";
  }
})(jQuery);
// Get current city name
// getCurrentCityName();
