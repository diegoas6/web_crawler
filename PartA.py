import io
import sys

VALID_CHARS = set(
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789'
    )

# Time Complexity: O(n)
# Where n is the number of characters in the document.
#
# In the while loop the whole document is read character by character, O(n).
# All the operations in the while loop are time constant O(1) in average.
# Therefore, the time complexity is linear O(n * 1) = O(n)
def tokenize(text):
    tokens = []
    new_token = ''
    for character in text:
        if character in VALID_CHARS:
            new_token += character
        else:
            if new_token:
                new_token = new_token.lower()
                tokens.append(new_token)
                new_token = ''
    if new_token:
        new_token = new_token.lower()
        tokens.append(new_token)
    return tokens

# Time Complexity: O(t)
# Where t is the number of tokens in the document
#
# The for loop iterates through the list of tokens once, O(t).
# wordFreq[token] = wordFreq.get(token, 0) + 1 time complexity is O(1).
# Therefore, time complexity is linear O(t * 1) = O(t).
def computeWordFrequencies(tokens):
    wordFreq = {}

    for token in tokens:
        wordFreq[token] = wordFreq.get(token, 0) + 1

    return wordFreq

# Time Complexity: O(u log u)
# Where u is the number of unique tokens.
#
# For loop iterates through the dict of unique tokens once, O(u).
# The sorted() function's time complexity is O(u logu).
# Therefore, the time complexity of the function is O(u + u log u) = O(u log u).
def printFrequencies(wordFreq):
    for token, count in sorted(wordFreq.items(), key=lambda item: (-item[1], item[0])):
        print(token + " -> " + str(count))


# Time complexity:
# Average and best case: O(n)
# Worst case: O(n log n), when the document consists entirely of
# different one-character unique tokens (e.g., "a b c d e f g h...")
#
# The time complexity is O(n + t + u log u), where n is the number of characters
# in the document, t the number of tokens, and u the number of unique tokens.
# In average n >> t > u, therefore, O(n + t + u log u) ≈ O(n)
def main():
    if len(sys.argv) != 2:
        print("Usage: python PartA.py <filename>")
        sys.exit(1)

    file = sys.argv[1]
    tokens = tokenize(file)
    wordFreq = computeWordFrequencies(tokens)
    printFrequencies(wordFreq)

if __name__ == "__main__":
    main()