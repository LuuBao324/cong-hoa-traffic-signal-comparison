# Field signal observations and interpretation

The user supplied complete phase durations measured from colour changes. Yellow is 3 seconds and is recorded separately from red. The observation date, time period and repeated-cycle sample count were not supplied. The original location and movement labels are retained in `survey_observations.csv`.

## Corridor observations

Towards Truong Chinh, the supplied through-movement red/green durations are 35/50 seconds at Hoang Hoa Tham, 26/53 at Ngo Be, 32/55 at Ap Bac, 36/60 at Tan Ky Tan Quy and 57/40 at C12. Ngo Be and Ap Bac share a merged controller. The user selected the Ap Bac timings for that controller. At Truong Chinh, the observed U-turn is 42 seconds red and 36 seconds green, with the specified through movement continuously green.

Towards Hoang Van Thu, the original red observations were 32 seconds at 18E, 41 at Ut Tich and 68 at the Hoang Van Thu roundabout. The roundabout through movement has 32 seconds green.

## Confirmed 18E programme

Both Cong Hoa through directions receive green together for 67 seconds. The side-road exits, permitted outer left turns and outer U-turns share a 29-second green stage. Each stage is followed by 3 seconds yellow. The resulting cycle is 102 seconds. Through red is 32 seconds, and the other group has 70 seconds red. The originally reported 67-second red is retained separately for traceability. The user explicitly kept the 29-second green after a later table showed 32 seconds.

The centre carriageway serves through traffic. Its left-turn, U-turn and opposite-direction return connections are removed. Large vehicles are prohibited from the restricted outer left turn into 18E. Yielding greens are selected where existing conflict or merging relationships require them.

## Ut Tich correction

The user chose to preserve red durations with separate 3-second yellow intervals. Ut Tich outgoing movements and the corridor U-turn receive 38 seconds green and 67 seconds red. Cong Hoa through movements receive 64 seconds green and 41 seconds red. The cycle is 108 seconds. Ut Tich vehicles can turn left or right into Cong Hoa. The return movement back into Ut Tich is removed.

## Other confirmed changes

At Hoang Hoa Tham, the corridor through and left-turn movements share the same stage. Turns yield where required by the network conflict model. The requested corridor left turn into Tan Ky Tan Quy is removed. Generated ordinary routes avoid U-turns.

For the other competing two-stage junctions, each stage receives 30 seconds green and 3 seconds yellow. Each group therefore has 33 seconds red and a 66-second cycle. A single noncompeting group can remain green. Opposing crossing stages at surveyed junctions use the observed red duration minus the separate yellow interval. This is the user's requested phase-allocation assumption.

The source network is manually edited. Signal and connection changes should be reviewed in NetEdit and checked through a common-input simulation before interpreting controller performance.
