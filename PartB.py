from PartA import tokenize, computeWordFrequencies
import sys

# Time complexity: O(n1 + n2), where n1 is the number of characters of file1
# and n2 is the number of character of file2.
#
# O(n1 + n2 + t1), n1 >> t1 in average. Then, time complexity is linear with respect
# to number of characters in the files => O(n1 + n2).
def fileTokensIntersection(file1, file2):
    tokens1 = computeWordFrequencies(tokenize(file1))  # O(n1)
    tokens2 = computeWordFrequencies(tokenize(file2))  # O(n2)

    intersection = []
    for token in tokens1:                              # O(t1), t1 is the number of unique tokens in file1
        if token in tokens2:                           # O(1)
            intersection.append(token)

    return intersection


# Time complexity: O(n1 + n2), where n1 is the number of characters of file1
# and n2 is the number of character of file2.
def main():
    if len(sys.argv) != 3:
        print("Usage: python PartB.py <file1> <file2>")
        sys.exit(1)

    files_intersection = fileTokensIntersection(sys.argv[1], sys.argv[2])
    print(len(files_intersection))


if __name__ == '__main__':
    main()

