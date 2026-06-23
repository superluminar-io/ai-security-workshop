# Cross-Customer Data Access

Throughout the previous modules, accessing another customer’s data was never restricted. You could look up `cust_002`’s profile, read their orders, and use that information to carry out refunds, discounts, and emails on their behalf — all while logged in as `cust_001`.

In the solutions for each module to this point we've added an auth check within the tool implementation. The tests should have returned green, but not all is as it seems.

We'll skip the hacking part since we've already established that you are able to access other customers' data. Go directly to the SOLUTION.md section to see how we can fix this issue.

