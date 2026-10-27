Feature: Capacity allocation

Scenario: Reserve the remaining capacity
  Given inputs available=3, reserved=2, q=3
  When allocate is requested
  Then acceptance is true
  And available is 0
  And reserved is 5

Scenario: No remaining capacity
  Given inputs available=0, reserved=5, q=1
  When allocate is requested
  Then acceptance is false
  And available is 0
  And reserved is 5
