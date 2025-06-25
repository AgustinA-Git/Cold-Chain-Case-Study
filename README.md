# Cold Chain Spoilage Analysis – Case Study

This project explores a simulated cold chain logistics dataset to identify the key factors that contribute to product spoilage during temperature-sensitive shipments. Using descriptive statistics and visual analytics, we analyze how variables such as transit time, ambient temperature, packaging type, and temperature excursions impact the likelihood and cost of spoilage.

The dataset includes the following fields:

- Order ID: Unique identifier for each shipment

- Product Type: Frozen, Refrigerated, or Ambient

- Order Weight (lbs): Shipment weight in pounds

- Origin DC / Destination: Distribution center and endpoint

- Distance miles and Transit Time hr: Route metrics

- Packaging Type: Type of thermal protection used

- Ambient Temperature (C): Temperature at origin

- Carrier, Shipment Cost (USD), Delivery Time Window

- Temp_Excursion: Deviation from optimal temperature

- Spoilage? (Binary): Flag indicating spoilage

- Spoilage Cost (USD): Associated financial loss

Objective
The goal is to determine which operational factors most strongly influence spoilage, enabling smarter decisions in packaging, routing, and scheduling to minimize waste and financial loss.
