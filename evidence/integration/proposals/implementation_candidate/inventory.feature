Feature: Component assembly

Scenario: The last complete kit can be assembled
  Given inputs a=2, b=1, f=0, q=1
  When assemble is requested
  Then acceptance is true
  And a is 0
  And b is 0
  And f is 1

Scenario: Empty inventory refuses without changing state
  Given inputs a=0, b=0, f=3, q=1
  When assemble is requested
  Then acceptance is false
  And a is 0
  And b is 0
  And f is 3

Scenario: Partial stock cannot produce a finished item
  Given inputs a=4, b=1, f=0, q=2
  When assemble is requested
  Then acceptance is false
  And a is 4
  And b is 1
  And f is 0

Scenario: Zero quantity is refused
  Given inputs a=8, b=8, f=1, q=0
  When assemble is requested
  Then acceptance is false
  And a is 8
  And b is 8
  And f is 1

Scenario: Multiple kits preserve resource accounting
  Given inputs a=9, b=5, f=2, q=3
  When assemble is requested
  Then acceptance is true
  And a is 3
  And b is 2
  And f is 5
