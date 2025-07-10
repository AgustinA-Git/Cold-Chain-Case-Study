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

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# LP Optimization Template 

In this model, we simulate a cold chain delivery problem where a truck carries a fixed number of boxes with temperature-sensitive goods. 
It’s fully configurable so you can adjust parameters and constraints to explore trade-offs between cooling costs and spoilage risk under different scenarios.
The challenge is to determine the optimal quantities of dry ice and gel packs to load, balancing two key costs:

Cooling costs — the expenses of adding dry ice and gel packs.

Spoilage costs — the expected financial loss from boxes that spoil if not kept cold enough.

After analyzing the dataset, research indicates that investing more in gel packs and dry ice significantly reduces spoilage. The critical question becomes:

How much should we actually spend on these cooling methods to minimize total expected costs?

The model takes into account:

The effectiveness of each unit of dry ice and gel packs in reducing spoilage probability,

The cost per unit of each cooling method,

The value lost for each spoiled box, and

The total number of boxes loaded.

The goal is to minimize overall costs, combining both direct cooling expenses and the expected spoilage losses.
