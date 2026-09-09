import json
import unittest

from omr.grade_answers import create_grading_result


class StructuredGradingResultsTests(unittest.TestCase):
    def test_result_is_json_serializable_and_has_question_details(self):
        answers = {
            1: "A",
            2: "BLANK",
            3: "MULTIPLE",
            4: "A",
        }
        answer_key = {question_number: "A" for question_number in range(1, 51)}
        answer_key.update({
            1: "A",
            2: "B",
            3: "C",
            4: "D",
        })

        result = create_grading_result(
            answers,
            answer_key,
            source_file="samples/example.png",
        )

        self.assertEqual(result["source_file"], "samples/example.png")
        self.assertEqual(result["total_questions"], 50)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["wrong"], 49)
        self.assertEqual(result["blank"], 1)
        self.assertEqual(result["multiple"], 1)
        self.assertEqual(len(result["questions"]), 50)
        self.assertEqual(result["questions"][0], {
            "question_number": 1,
            "student_answer": "A",
            "correct_answer": "A",
            "result": "CORRECT",
        })
        self.assertEqual(result["questions"][1]["result"], "BLANK")
        self.assertEqual(result["questions"][2]["result"], "MULTIPLE")
        self.assertEqual(result["questions"][3]["result"], "WRONG")
        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
