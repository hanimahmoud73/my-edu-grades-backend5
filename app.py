import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np # For statistical calculations
from datetime import datetime

app = Flask(__name__)
# تم تعديل هذا السطر للسماح بنطاق Netlify المحدد والاختبار المحلي
CORS(app, resources={r"/*": {"origins": ["https://dancing-crepe-991005.netlify.app", "http://localhost:5500"]}})

# --- إعدادات حدود التحليل ---
MONTHLY_LIMIT = 10
# *** هام: هذا الكود السري يجب أن يكون قوياً جداً في بيئة الإنتاج! ***
# يجب أن يتطابق مع 'API_SECRET_CODE' في الواجهة الأمامية (index.html)
# تم تعديل هذا السطر ليقرأ الكود السري من متغيرات البيئة
SECRET_CODE = os.getenv("SECRET_CODE", "default_dev_secret_replace_me") 

# لبيانات تتبع الاستخدام: IP -> {'count': int, 'month': int, 'year': int}
# ملاحظة: هذا القاموس يحفظ البيانات في الذاكرة. ستُفقد البيانات عند إعادة تشغيل الخادم.
user_analysis_tracking = {}

# Default absolute grades configuration (should match frontend)
DEFAULT_ABSOLUTE_GRADES_CONFIG = [
    {'letter': 'A', 'min': 90, 'max': 100, 'word': 'ممتاز', 'color': '#10B981'},
    {'letter': 'B', 'min': 80, 'max': 89, 'word': 'جيد جداً', 'color': '#6366F1'},
    {'letter': 'C', 'min': 65, 'max': 79, 'word': 'جيد', 'color': '#2196F3'},
    {'letter': 'D', 'min': 50, 'max': 64, 'word': 'مقبول', 'color': '#F59E0B'},
    {'letter': 'H', 'min': 0, 'max': 49, 'word': 'ضعيف', 'color': '#EF4444'}
]

# Translations for backend-generated text (simplified, should match frontend translations for consistency)
TRANSLATIONS = {
    'ar': {
        'zScoreExcellentWord': 'ممتاز',
        'zScoreVeryGoodPlusWord': 'جيد جدًا+',
        'zScoreVeryGoodWord': 'جيد جدًا',
        'zScoreGoodPlusWord': 'جيد+',
        'zScoreGoodWord': 'جيد',
        'zScoreAcceptableWord': 'مقبول',
        'zScoreWeakWord': 'ضعيف',
        'notClassified': 'غير مصنف',
        'notSpecified': 'غير محدد',
        'students': 'طلاب',
        'meanInsightPrefix': 'المتوسط الحسابي (',
        'meanInsightSuffix': '): يمثل مستوى الأداء العام للفصل. ',
        'meanHigh': 'يشير متوسط الدرجات المرتفع هذا إلى فهم قوي للمادة من قبل معظم الطلاب.',
        'meanMedium': 'متوسط الدرجات جيد، مما يدل على استيعاب معقول للمادة. يمكن التركيز على رفع مستوى الطلاب المتوسطين.',
        'meanLow': 'متوسط الدرجات منخفض. قد يكون من الضروري إعادة تقييم طرق التدريس أو صعوبة المحتوى لمساعدة الطلاب.',
        'stdDevInsightPrefix': 'الانحراف المعياري (',
        'stdDevInsightSuffix': '): يقيس مدى تباين درجات الطلاب حول المتوسط. ',
        'stdDevLow': 'انحراف معياري منخفض جدًا يشير إلى أن أداء الطلاب متقارب ومستواهم متجانس.',
        'stdDevMedium': 'انحراف معياري متوسط يدل على وجود بعض التباين في أداء الطلاب، مما يتطلب اهتماماً فردياً بالفئات المختلفة.',
        'stdDevHigh': 'انحراف معياري مرتفع يشير إلى وجود تباين كبير في مستويات الطلاب. بعض الطلاب متفوقون جداً والبعض الآخر يواجه صعوبات كبيرة. هذا يتطلب استراتيجيات تدريس تفاضلية.',
        'rangeInsightPrefix': 'المدى (',
        'rangeInsightMiddle': ' = ',
        'rangeInsightSuffix': '): يمثل الفارق بين أعلى وأقل درجة. ',
        'rangeNarrow': 'مدى ضيق يشير إلى أن جميع الطلاب يؤدون ضمن نطاق محدود من الدرجات، مما قد يدل على سهولة الاختبار أو تجانس الفصل.',
        'rangeWide': 'مدى واسع يشير إلى تباين كبير في الأداء بين أعلى وأقل طالب. هذا يؤكد الحاجة إلى استراتيجيات دعم للمتأخرين وإثراء للمتفوقين.',
        'zScoreGroupExcellent': 'وجود عدد كبير من الطلاب الممتازين (بناءً على Z-Score) يدل على فعالية التدريس أو ارتفاع مستوى الدفعة بأكمله. يمكن الاستفادة منهم كقادة للمجموعات، أو تقديم محتوى إثرائي إضافي لهم.',
        'zScoreGroupWeak': 'نسبة الطلاب في فئة "ضعيف" (بناءً على Z-Score) تزيد عن 20%. يُنصح بتقديم خطط دعم إضافية، جلسات تقوية مكثفة، أو دروس فردية لهؤلاء الطلاب لرفع مستواهم.',
        'zScoreGroupHighVariance': 'التقييم النسبي يوضح تباينًا كبيرًا في أداء الطلاب. فكر في مجموعات دعم صغيرة للطلاب المتأخرين ومسارات تعليمية متباينة لتلبية الاحتياجات الفردية.',
        'zScoreGroupLowVariance': 'التقييم النسبي يظهر أن أداء الطلاب متقارب. هذا يسهل التدريس الموجه للمجموعة ككل، ويمكن التركيز على تعزيز نقاط القوة المشتركة.',
        'absoluteGroupHighOverall': 'الفصل بأكمله يحقق درجات عالية جدًا بناءً على السلم المطلق. هذا يعكس استيعابًا ممتازًا للمادة، ويمكن تحديهم بمهام أكثر تعقيدًا.',
        'absoluteGroupLowOverall': 'متوسط درجات الفصل منخفض جداً في التقييم المطلق. قد يتطلب الأمر مراجعة شاملة للمنهج، تعديل استراتيجيات التدريس، أو توفير مواد تعليمية إضافية.',
        'absoluteGroupManyExcellent': 'هناك نسبة كبيرة من الطلاب حصلت على تقديرات ممتازة (أو ما يعادلها في سلمك المطلق). حافظ على هذا المستوى وشجعهم على الإثراء الأكاديمي، أو إشراكهم في أنشطة تحدي إضافية.',
        'absoluteGroupManyWeak': 'عدد الطلاب الحاصلين على تقدير ضعيف (أو ما يعادله في سلمك المطلق) مرتفع. يجب تحديد هؤلاء الطلاب وتقديم الدعم الفردي لهم، مع تتبع تقدمهم بشكل مستمر.',
        'individualExcellent': 'الطالب <strong>[اسم الطالب]</strong> أداؤه ممتاز/جيد جدًا. يمكن تشجيعه على مساعدة زملائه، أو إعطائه مهام إثرائية لتنمية مهاراته، أو تكليفه بمشاريع بحثية متقدمة.',
        'individualWeak': 'الطالب <strong>[اسم الطالب]</strong> يواجه صعوبات. يُنصح بعقد جلسة فردية معه لفهم أسباب تراجع مستواه ووضع خطة دعم مناسبة، مثل مراجعات إضافية أو استخدام أساليب تعلم بديلة.',
        'individualAverage': 'الطالب <strong>[اسم الطالب]</strong> أداؤه متوسط. يمكن تحفيزه عبر تحديد أهداف قصيرة المدى وواضحة، ومتابعتها معه لرفع مستواه، وتقديم تغذية راجعة بناءة.',
        'addManualRecommendationTitle': 'توصية يدوية:',
        'minTwoStudentsRequired': 'للتحليل الإحصائي الدقيق، يتطلب البرنامج طالبين على الأقل.',
        'unauthorizedAccess': 'خطأ في المصادقة: وصول غير مصرح به.',
        'monthlyLimitExceeded': 'لقد استهلكت الحد المجاني الشهري. يُرجى الانتظار للشهر التالي أو الترقية.',
        'remainingAnalysesMessage': 'بقي لديك {remaining} تحليلات هذا الشهر.',
        'internalError': 'حدث خطأ داخلي في الخادم.',
        'processingError': 'خطأ في معالجة البيانات.' # رسالة إضافية لأخطاء التحليل غير المحددة
    },
    'en': {
        'zScoreExcellentWord': 'Excellent',
        'zScoreVeryGoodPlusWord': 'Very Good+',
        'zScoreVeryGoodWord': 'Very Good',
        'zScoreGoodPlusWord': 'Good+',
        'zScoreGoodWord': 'Good',
        'zScoreAcceptableWord': 'Acceptable',
        'zScoreWeakWord': 'Weak',
        'notClassified': 'Unclassified',
        'notSpecified': 'Not Specified',
        'students': 'students',
        'meanInsightPrefix': 'Mean (',
        'meanInsightSuffix': '): Represents the overall performance level of the class. ',
        'meanHigh': 'This high average score indicates a strong understanding of the material by most students.',
        'meanMedium': 'The average grade is good, indicating reasonable comprehension of the material. Focus can be placed on raising the level of average students.',
        'meanLow': 'The average grade is low. It may be necessary to reassess teaching methods or content difficulty to help students.',
        'stdDevInsightPrefix': 'Standard Deviation (',
        'stdDevInsightSuffix': '): Measures the spread of student scores around the mean. ',
        'stdDevLow': 'A very low standard deviation indicates that student performance is consistent and homogeneous.',
        'stdDevMedium': 'A moderate standard deviation indicates some variation in student performance, requiring individual attention to different groups.',
        'stdDevHigh': 'A high standard deviation indicates significant variation in student levels. Some students are very advanced, while others face significant difficulties. This requires differentiated teaching strategies.',
        'rangeInsightPrefix': 'Range (',
        'rangeInsightMiddle': ' = ',
        'rangeInsightSuffix': '): Represents the difference between the highest and lowest grades. ',
        'rangeNarrow': 'A narrow range indicates that all students perform within a limited range of scores, which may suggest an easy test or a homogeneous class.',
        'rangeWide': 'A wide range indicates significant variation in performance between the highest and lowest student. This emphasizes the need for support strategies for struggling students and enrichment for advanced ones.',
        'zScoreGroupExcellent': 'A large number of excellent students (based on Z-Score) indicates effective teaching or a generally high-performing cohort. They can be leveraged as group leaders or provided with additional enrichment content.',
        'zScoreGroupWeak': 'The percentage of students in the "Weak" category (based on Z-Score) exceeds 20%. It is recommended to provide additional support plans, intensive tutoring sessions, or individual lessons for these students to improve their level.',
        'zScoreGroupHighVariance': 'Relative grading shows significant variance in student performance. Consider small support groups for struggling students and differentiated learning paths to meet individual needs.',
        'zScoreGroupLowVariance': 'Relative grading shows that student performance is consistent. This facilitates group-oriented teaching and allows focusing on reinforcing common strengths.',
        'absoluteGroupHighOverall': 'The entire class achieves very high scores based on the absolute scale. This reflects excellent comprehension of the material, and they can be challenged with more complex tasks.',
        'absoluteGroupLowOverall': 'The average class grade is very low in absolute grading. This may require a comprehensive curriculum review, adjustment of teaching strategies or provision of additional learning materials.',
        'absoluteGroupManyExcellent': 'A large percentage of students received excellent grades (or equivalent in your absolute scale). Maintain this level and encourage them for academic enrichment, or involve them in additional challenging activities.',
        'absoluteGroupManyWeak': 'The number of students receiving a "Weak" grade (or equivalent in your absolute scale) is high. These students should be identified and provided with individual support, with continuous monitoring of their progress.',
        'individualExcellent': 'Student <strong>[Student Name]</strong> has excellent/very good performance. They can be encouraged to help peers, given enrichment tasks to develop their skills, or assigned advanced research projects.',
        'individualWeak': 'Student <strong>[Student Name]</strong> is facing difficulties. It is recommended to hold an individual session with them to understand the reasons for their low performance and develop a suitable support plan, such as additional reviews or alternative learning methods.',
        'individualAverage': 'Student <strong>[Student Name]</strong> has average performance. They can be motivated by setting clear short-term goals, following up on their progress, and providing constructive feedback.',
        'addManualRecommendationTitle': 'Manual Recommendation:',
        'minTwoStudentsRequired': 'For accurate statistical analysis, the program requires at least two students.',
        'unauthorizedAccess': 'Authentication Error: Unauthorized access.',
        'monthlyLimitExceeded': 'You have consumed your free monthly limit. Please wait for the next month or upgrade.',
        'remainingAnalysesMessage': '{remaining} analyses remaining this month.',
        'internalError': 'Internal server error occurred.',
        'processingError': 'Data processing error.'
    }
}

def get_translation(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS['ar']).get(key, f"Missing translation for {key}")

@app.route('/analyze', methods=['POST'])
def analyze_grades():
    # 1. التحقق من الكود السري المرسل من الواجهة الأمامية
    provided_secret_code = request.headers.get('X-Secret-Code')
    if provided_secret_code != SECRET_CODE:
        return jsonify({
            "error": "Unauthorized access",
            "message": get_translation(request.json.get('current_language', 'ar'), 'unauthorizedAccess')
        }), 401

    # 2. الحصول على عنوان IP للمستخدم (مع دعم X-Forwarded-For)
    # هذا مهم عند النشر على منصات مثل Render حيث قد يمر الطلب عبر بروكسيات
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # 3. التحقق من حد الاستخدام الشهري لعنوان IP هذا
    if user_ip not in user_analysis_tracking:
        user_analysis_tracking[user_ip] = {'count': 0, 'month': current_month, 'year': current_year}
    
    # إذا كان شهراً جديداً، أعد تعيين العداد
    if user_analysis_tracking[user_ip]['month'] != current_month or \
       user_analysis_tracking[user_ip]['year'] != current_year:
        user_analysis_tracking[user_ip] = {'count': 0, 'month': current_month, 'year': current_year}

    # التحقق من تجاوز الحد
    if user_analysis_tracking[user_ip]['count'] >= MONTHLY_LIMIT:
        remaining_analyses = 0
        return jsonify({
            "error": "Monthly limit exceeded",
            "remaining_analyses": remaining_analyses, # لتحديث الواجهة الأمامية بالرقم صفر
            "message": get_translation(request.json.get('current_language', 'ar'), 'monthlyLimitExceeded')
        }), 429 # 429 Too Many Requests

    # 4. معالجة طلب التحليل الفعلي بعد اجتياز التحقق
    try:
        data = request.get_json()
        
        students_data = data.get('students', [])
        grading_system = data.get('grading_system', 'absolute')
        max_final_grade = data.get('max_final_grade', 100)
        absolute_grades_config = data.get('absolute_grades_config', DEFAULT_ABSOLUTE_GRADES_CONFIG)
        manual_recommendations_added = data.get('manual_recommendations', '')
        current_language = data.get('current_language', 'ar')
        display_format = data.get('display_format', 'both')

        grades = [s['grade'] for s in students_data if isinstance(s.get('grade'), (int, float))]

        if not grades or len(grades) < 2:
            return jsonify({
                'error': get_translation(current_language, 'minTwoStudentsRequired'),
                'message': get_translation(current_language, 'minTwoStudentsRequired') # رسالة للواجهة الأمامية
            }), 400

        # Calculate statistics
        n = len(grades)
        grades_array = np.array(grades)
        mean = float(np.mean(grades_array))
        stddev = float(np.std(grades_array, ddof=1) if n > 1 else 0.0) # ddof=1 for sample std dev
        highest = float(np.max(grades_array))
        lowest = float(np.min(grades_array))

        stats = {
            'count': n,
            'mean': round(mean, 2),
            'stddev': round(stddev, 2),
            'max': highest,
            'min': lowest
        }

        classified_students = []
        for student in students_data:
            grade = student['grade']
            classification_info = {}
            z_score = None

            if grading_system == 'z_score':
                z_score = round(((grade - mean) / stddev), 2) if stddev > 0 else 0.0
                classification_info = get_z_score_classification(z_score, current_language)
            else: # absolute
                classification_info = get_absolute_classification(grade, absolute_grades_config, current_language)
            
            classified_students.append({
                'name': student['name'],
                'grade': student['grade'],
                'zScore': z_score,
                'classification_info': classification_info
            })
        
        # Sort students by grade for display
        classified_students.sort(key=lambda s: s['grade'], reverse=True)

        # Calculate grade distribution for charts
        grade_counts = {}
        for student in classified_students:
            classification_text = get_classification_text(student['classification_info'], display_format)
            if classification_text not in grade_counts:
                grade_counts[classification_text] = {'count': 0, 'color': student['classification_info']['color'], 'order': get_classification_order(student['classification_info'], grading_system, absolute_grades_config)}
            grade_counts[classification_text]['count'] += 1
        
        # Sort grade counts based on their defined order for consistent chart display
        grade_counts_sorted = sorted(grade_counts.items(), key=lambda item: item[1]['order'])

        # Generate recommendations
        recommendations = generate_recommendations(stats, classified_students, grading_system, max_final_grade, absolute_grades_config, manual_recommendations_added, current_language)

        # 5. زيادة العداد بعد التحليل الناجح فقط
        user_analysis_tracking[user_ip]['count'] += 1
        remaining_analyses = MONTHLY_LIMIT - user_analysis_tracking[user_ip]['count']
        
        return jsonify({
            'stats': stats,
            'classified_students': classified_students,
            'grade_counts_sorted': grade_counts_sorted,
            'recommendations': recommendations,
            'grading_system': grading_system, # Return this to frontend to control Z-score column visibility
            "remaining_analyses": remaining_analyses,
            "message": get_translation(current_language, 'remainingAnalysesMessage').format(remaining=remaining_analyses)
        }), 200

    except Exception as e:
        # التعامل مع أي أخطاء تحدث أثناء عملية التحليل
        print(f"Error during analysis: {e}") # لطباعة الخطأ في سجلات الخادم
        return jsonify({
            "error": "Processing Error",
            "message": get_translation(current_language, 'processingError') # رسالة عامة للواجهة الأمامية
        }), 500

def get_absolute_classification(grade, config, lang):
    for entry in config:
        if entry['min'] <= grade <= entry['max']:
            return {'letter': entry['letter'], 'word': entry['word'], 'color': entry['color']}
    return {'letter': 'N/A', 'word': get_translation(lang, 'notClassified'), 'color': '#888888'}

def get_z_score_classification(z_score, lang):
    if z_score > 1.5: return {'letter': 'A', 'word': get_translation(lang, 'zScoreExcellentWord'), 'color': '#10B981'}
    if z_score > 1.0: return {'letter': 'B+', 'word': get_translation(lang, 'zScoreVeryGoodPlusWord'), 'color': '#4CAF50'}
    if z_score > 0.5: return {'letter': 'B', 'word': get_translation(lang, 'zScoreVeryGoodWord'), 'color': '#6366F1'}
    if z_score > 0.0: return {'letter': 'C+', 'word': get_translation(lang, 'zScoreGoodPlusWord'), 'color': '#3B82F6'}
    if z_score > -0.5: return {'letter': 'C', 'word': get_translation(lang, 'zScoreGoodWord'), 'color': '#2196F3'}
    if z_score > -1.0: return {'letter': 'D', 'word': get_translation(lang, 'zScoreAcceptableWord'), 'color': '#F59E0B'}
    return {'letter': 'F', 'word': get_translation(lang, 'zScoreWeakWord'), 'color': '#EF4444'}

def get_classification_text(classification_info, display_format):
    if not classification_info:
        return "غير مصنف" # Fallback
    
    letter = classification_info.get('letter', '')
    word = classification_info.get('word', '')

    if display_format == 'letter':
        return letter
    if display_format == 'word':
        return word
    return f"{letter} - {word}"

def get_classification_order(classification_info, grading_system, absolute_grades_config):
    if grading_system == 'absolute':
        # Sort absolute grades config in descending order by min score to match display
        sorted_config = sorted(absolute_grades_config, key=lambda x: x['min'], reverse=True)
        for idx, cfg in enumerate(sorted_config):
            if cfg['letter'] == classification_info['letter']:
                return idx
        return float('inf') # Fallback for unclassified
    else: # z_score
        z_order = ['A', 'B+', 'B', 'C+', 'C', 'D', 'F']
        try:
            return z_order.index(classification_info['letter'])
        except ValueError:
            return float('inf') # Fallback for unclassified

def generate_recommendations(stats, classified_students, grading_system, max_final_grade, absolute_grades_config, manual_recommendations_added, lang):
    statistical_insights = []
    group_recommendations = []
    individual_recommendations = []

    # Statistical Insights
    mean_insight = get_translation(lang, 'meanInsightPrefix') + str(stats['mean']) + get_translation(lang, 'meanInsightSuffix')
    if stats['mean'] >= (max_final_grade * 0.8):
        mean_insight += get_translation(lang, 'meanHigh')
    elif stats['mean'] >= (max_final_grade * 0.6):
        mean_insight += get_translation(lang, 'meanMedium')
    else:
        mean_insight += get_translation(lang, 'meanLow')
    statistical_insights.append(mean_insight)

    std_dev_insight = get_translation(lang, 'stdDevInsightPrefix') + str(stats['stddev']) + get_translation(lang, 'stdDevSuffix')
    if stats['stddev'] < (max_final_grade * 0.1):
        std_dev_insight += get_translation(lang, 'stdDevLow')
    elif stats['stddev'] >= (max_final_grade * 0.1) and stats['stddev'] <= (max_final_grade * 0.2):
        std_dev_insight += get_translation(lang, 'stdDevMedium')
    else:
        std_dev_insight += get_translation(lang, 'stdDevHigh')
    statistical_insights.append(std_dev_insight)

    grade_range = stats['max'] - stats['min']
    range_insight = get_translation(lang, 'rangeInsightPrefix') + str(stats['min']) + ' - ' + str(stats['max']) + get_translation(lang, 'rangeInsightMiddle') + str(round(grade_range, 2)) + get_translation(lang, 'rangeInsightSuffix') # Round range for display
    if grade_range < (max_final_grade * 0.2):
        range_insight += get_translation(lang, 'rangeNarrow')
    else:
        range_insight += get_translation(lang, 'rangeWide')
    statistical_insights.append(range_insight)

    # Group Recommendations
    if grading_system == 'z_score':
        excellent_count = sum(1 for s in classified_students if s['classification_info']['letter'] == 'A' or s['classification_info']['letter'] == 'B+')
        weak_count = sum(1 for s in classified_students if s['classification_info']['letter'] == 'F')
        
        if excellent_count > (stats['count'] * 0.2):
            group_recommendations.append(get_translation(lang, 'zScoreGroupExcellent'))
        if weak_count > (stats['count'] * 0.2):
            group_recommendations.append(get_translation(lang, 'zScoreGroupWeak'))
        if stats['stddev'] > 1.0:
            group_recommendations.append(get_translation(lang, 'zScoreGroupHighVariance'))
        else: # Consider if stddev is very low (implies homogeneity)
            group_recommendations.append(get_translation(lang, 'zScoreGroupLowVariance'))
    else: # Absolute Grading
        # Make sure to use the actual 'A' and 'H' classifications from config if they exist
        # Default 'A' is 90-100, 'H' is 0-49
        excellent_absolute_count = sum(1 for s in classified_students if s['classification_info']['letter'] == 'A')
        weak_absolute_count = sum(1 for s in classified_students if s['classification_info']['letter'] == 'H')
        
        if stats['mean'] >= (max_final_grade * 0.9):
            group_recommendations.append(get_translation(lang, 'absoluteGroupHighOverall'))
        elif stats['mean'] < (max_final_grade * 0.6):
            group_recommendations.append(get_translation(lang, 'absoluteGroupLowOverall'))
        
        if excellent_absolute_count > (stats['count'] * 0.3):
            group_recommendations.append(get_translation(lang, 'absoluteGroupManyExcellent'))
        if weak_absolute_count > (stats['count'] * 0.2):
            group_recommendations.append(get_translation(lang, 'absoluteGroupManyWeak'))

    # Individual Recommendations (find one example for each category if available)
    excellent_student = next((s for s in classified_students if s['classification_info']['letter'] in ['A', 'B+']), None)
    weak_student = next((s for s in classified_students if s['classification_info']['letter'] == 'F'), None)
    average_student = next((s for s in classified_students if s['classification_info']['letter'] in ['C', 'D']), None)

    if grading_system == 'absolute':
        excellent_student = next((s for s in classified_students if s['classification_info']['letter'] == 'A'), None)
        weak_student = next((s for s in classified_students if s['classification_info']['letter'] == 'H'), None)
        # For absolute, 'B', 'C', 'D' can represent average. Prioritize 'C' then 'D' then 'B' for 'average' example
        average_student = next((s for s in classified_students if s['classification_info']['letter'] == 'C'), 
                                next((s for s in classified_students if s['classification_info']['letter'] == 'D'),
                                     next((s for s in classified_students if s['classification_info']['letter'] == 'B'), None)))

    # Ensure unique students are picked for individual recommendations
    selected_students_names = set()

    if excellent_student and excellent_student['name'] not in selected_students_names:
        individual_recommendations.append(get_translation(lang, 'individualExcellent').replace('[اسم الطالب]', excellent_student['name']).replace('[Student Name]', excellent_student['name']))
        selected_students_names.add(excellent_student['name'])

    if weak_student and weak_student['name'] not in selected_students_names:
        individual_recommendations.append(get_translation(lang, 'individualWeak').replace('[اسم الطالب]', weak_student['name']).replace('[Student Name]', weak_student['name']))
        selected_students_names.add(weak_student['name'])

    if average_student and average_student['name'] not in selected_students_names:
        individual_recommendations.append(get_translation(lang, 'individualAverage').replace('[اسم الطالب]', average_student['name']).replace('[Student Name]', average_student['name']))
        selected_students_names.add(average_student['name'])

    if manual_recommendations_added.strip():
        group_recommendations.append(f"[{get_translation(lang, 'addManualRecommendationTitle')}]: {manual_recommendations_added}")

    return {
        'statistical_insights': statistical_insights,
        'group_recommendations': group_recommendations,
        'individual_recommendations': individual_recommendations
    }

# تم حذف هذا الجزء. Gunicorn هو الذي يشغل التطبيق على Render.
# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)