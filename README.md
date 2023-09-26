# EV Charging Cost Calculator Version 0.2

The EV Charging Cost Calculator is a python-based tool that calculates the electricity costs for charging a private electric vehicle (or fleet of electric vehicles on the same meter) or a public electric vehicle charging station. The main purpose of this tool is to enable cross-rate analyses of charging costs for any EV charging scenario. For example, it could be used to calculate the cost to operate a public DCFC charger across all supported utility rates available in the [OpenEI Utility Rate Database](https://openei.org/wiki/Utility_Rate_Database).

The EV Rate Calculator is licensed under the [MIT License](https://opensource.org/license/mit/) and is free to use and modify. 

If you use this calculator in your work, please cite it as follows:
>Atlas Public Policy, 2023. EV Charging Cost Calculator (v0.2). Washington, DC. www.github.com/AtlasPublicPolicy/ev-rate-calculator.

Funding for the development of this tool was generously provided by the National Resources Defense Council (NRDC).

* Download the latest release of the tool here: [ev-charging-cost-calculator-v0.2.zip](https://github.com/AtlasPublicPolicy/ev-charging-cost-calculator/archive/refs/tags/v0.2.zip) or from the [releases page](https://github.com/AtlasPublicPolicy/ev-charging-cost-calculator/releases/tag/v0.2)

* The user guide for this tool is available [here](documentation/user-guide.md).


*Disclaimer: This tool has had limited testing. It may contain bugs and may not work on all systems. Further, the tool is provided as-is and with no warranty. The authors and Atlas Public Policy make no guarantees about the accuracy of the tool or the results it produces. Support for the tool is limited. Please report bugs in the issues section of this repository. Current version: 0.2*

The tool is flexible and supports a wide range of charging scenarios, from large fleet installations or high power charging sites to small fleets and individual vehicles. Thus, the tool does little to limit the types of rates included in its analysis. As documented in the user guide (insert link), users are responsible for filtering outputs to remove those rates not applicable to the use case they are modeling. Failure to limit results to applicable rates will result in invalid cost estimates.*


## Functionality
The tool uses utility rates from the [OpenEI Utility Rate Database](https://openei.org/wiki/Utility_Rate_Database). The accuracy of this tool is dependent on the accuracy of the data in the OpenEI database. The tool is designed to be used with the OpenEI database as it exists at the time of the tool's release. Future updates to the OpenEI database may cause the tool to produce inaccurate results or fail. The tool is not designed to be used with custom rates that are not in the OpenEI database.

The tool supports most commonly-used utility rate structures in the United States.
* Flat or tiered volumetric (energy) rates
* Time-of-use (TOU) rates
* Flat or tiered Demand Charges
* Time-of-use (TOU) Demand Charges

The tool does not support:
* Rates with coincident demand charges
* Rates with ratcheting demand charges
* Rates where demand charges are assessed on a daily basis
* Complex rates with interacting tier and TOU components

The tool is designed to be used from the command line and so use requires comfort with simple command line interfaces. Future versions of the tool may include a web-based interface for accessibility and ease of use.

The EV Rate Calculator does not simulate charging behavior or energy and power requirements for charging vehicles. Users must model or these aspects of EV charging separately, use real-world charging data, or otherwise provide charging energy and power curves. Users provide both a 24-hour hourly average energy use, and hourly peak power use for the charging scenario. The tool supports both single-inputs (one 24-hour input) or monthly inputs (twelve 24-hour inputs). See the [Input Data](documentation/user-guide.md/###Input-Data) section in the [User Guide](documentation/user-guide.md) for more information on inputting data for the tool.

