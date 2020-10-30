{
    # Theme information
    'name' : 'Clarico Product Carousel',
    'category' : 'Website',
    'version' : '1.0',
    'summary': 'Website Product Carousel',
    'description': """""",

    # Dependencies
    'depends': [
        'clarico_snippets',
    ],

    # Views
    'data': [
        'security/ir.model.access.csv',     
        'data/product_carousel_filter_demo_data.xml',
        'data/product_carousel.xml',
        'views/website_filter_ept_view.xml',
        'templates/assets.xml',
        'templates/ecommerce_product_carousel_snippet.xml',
        'templates/snippet_options.xml',
        'views/website_multi_filter_ept_view.xml',
        'templates/product_static_carousel.xml',
        'templates/product_static_carousel_option.xml',
    ],

    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com',

    # Technical
    'installable': True,
}
