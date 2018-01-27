import sys

num_failed = 0
num_tests = 0

if len(sys.argv) < 2:
    print("Missing argument: <filename>")
    input()
    sys.exit(0)

with open(sys.argv[1], 'r') as transcript:
    lines = transcript.readlines()

    for i in range(len(lines)):
        line = lines[i]
        if line.startswith("# assert"):
            tokens = ["# St" + str(x) for x in line.split()[2:]]
            for j in range(len(tokens)):
                if tokens[j] != lines[i+j+1]:
                    num_failed += 1
                    print("Test failed on line " + str(i+1) + ": Expected " + tokens[j] + ", Actual: " + lines[i+j+i])

if num_failed == 0:
    print("All {0:d} test passed! (100.00%)".format(num_tests))
else:
    print('{0:d} tests failed ({1:.2f}%)'.format(num_failed, float(num_failed)/num_tests))

input()
