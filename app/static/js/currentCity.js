async function getCurrentCityName() {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(async (position) => {
      // Retrieve latitude and longitude
      const latitude = position.coords.latitude;
      const longitude = position.coords.longitude;

      try {
        // Call reverse geocoding API to get address details
        const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}`);
        const data = await response.json();

        // Extract city name from the address details
        const cityName = data.address.city;

        // Display city name
        console.log("Current city: " + cityName);
        resolve(cityName);
      } catch (error) {
        console.error("Error fetching location data: ", error);
        reject(error);
      }
    }, (error) => {
      console.error("Error getting user's location: ", error);
      reject(error);
    });
  });
}